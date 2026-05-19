"""
Module B — Cross-page consistency check.

Pull short factual claims from each crawled page (operating hours, cut-off
times, free-delivery thresholds, service area) and flag conflicts between
pages.

Heuristic, not exhaustive. False positives are acceptable; false negatives
on obvious contradictions are not.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..crawler import CrawlResult, FetchedPage


@dataclass
class ConflictSide:
    page_url: str
    page_intent: str
    value: str
    snippet: str


@dataclass
class Conflict:
    topic: str
    description: str
    sides: list[ConflictSide]


# ------------------------------ helpers ---------------------------------- #


def _windows(text: str, pattern: re.Pattern, span: int = 80) -> list[tuple[str, str]]:
    """Return [(match, surrounding_snippet)] for every match of `pattern`."""
    out: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        start = max(0, m.start() - span)
        end = min(len(text), m.end() + span)
        snippet = text[start:end].replace("\n", " ").strip()
        out.append((m.group(0).strip(), snippet))
    return out


def _norm_time(s: str) -> str:
    """Normalize a clock time like '5pm', '17:00', '5:00 PM' -> 'HH:MM'."""
    s = s.lower().replace(".", ":").strip()
    m = re.match(
        r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$", s, re.I
    )
    if not m:
        return s
    h = int(m.group(1))
    mm = int(m.group(2) or 0)
    suf = (m.group(3) or "").lower()
    if suf == "pm" and h < 12:
        h += 12
    if suf == "am" and h == 12:
        h = 0
    return f"{h:02d}:{mm:02d}"


# ------------------------------ extractors ------------------------------- #

CUTOFF_RE = re.compile(
    # Trigger: cut-off | order by | same-day ... before/by
    r"(?:cut[\s\-]?off|order\s+by|same[\s\-]?day[^.\n]{0,60}?(?:before|by))"
    # Then a clock value within 60 chars
    r"[^.\n]{0,60}?(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))",
    re.I | re.S,
)

FREE_DELIVERY_RE = re.compile(
    r"free\s+(?:shipping|delivery)[^.\n]{0,60}",
    re.I,
)

MIN_THRESHOLD_RE = re.compile(
    r"(?:above|over|orders?\s+(?:above|over)|min(?:imum)?\s+of?)\s*"
    r"([A-Z$£€¥]{0,4}\s?\$?\s?\d{1,5}(?:[.,]\d{2})?)",
    re.I,
)

NO_MIN_RE = re.compile(
    r"(no\s+min(?:imum)?|free\s+(?:shipping|delivery)\s+(?:on|for)\s+(?:all|every|any)\s+order)",
    re.I,
)

# Service area — country / state / city style mentions in shipping-ish contexts
AREA_RE = re.compile(
    r"(?:ship(?:ping)?|deliver(?:y|ies)?|available|serve|coverage)\s+(?:to|in|across|throughout)?\s+"
    r"([A-Z][A-Za-z]+(?:\s*(?:,|and|&)\s*[A-Z][A-Za-z]+){0,3})",
)

HOURS_RE = re.compile(
    r"(?:open|hours?|business\s+hours?)[^.\n]{0,40}?"
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*[-–to]+\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
    re.I,
)


def _extract_simple(page: FetchedPage, pattern: re.Pattern) -> list[tuple[str, str]]:
    """Generic value+snippet extractor."""
    out: list[tuple[str, str]] = []
    for m in pattern.finditer(page.text):
        val = m.group(1) if m.groups() else m.group(0)
        start = max(0, m.start() - 60)
        end = min(len(page.text), m.end() + 60)
        snippet = page.text[start:end].replace("\n", " ").strip()
        out.append((val.strip(), snippet))
    return out


# ---------------------------- main detectors ----------------------------- #


def detect_cutoff_conflicts(crawl: CrawlResult) -> Conflict | None:
    found: dict[str, list[ConflictSide]] = {}
    for p in crawl.pages:
        if not p.ok or not p.text:
            continue
        for m in CUTOFF_RE.finditer(p.text):
            raw = m.group(1)
            norm = _norm_time(raw)
            if not norm:
                continue
            start = max(0, m.start() - 60)
            end = min(len(p.text), m.end() + 60)
            snippet = p.text[start:end].replace("\n", " ").strip()
            found.setdefault(norm, []).append(
                ConflictSide(
                    page_url=p.final_url or p.url,
                    page_intent=p.intent,
                    value=raw.strip(),
                    snippet=snippet,
                )
            )

    if len(found) >= 2:
        # pick the two most different values
        keys = list(found.keys())
        sides = [found[k][0] for k in keys[:2]]
        return Conflict(
            topic="Same-day delivery cut-off time",
            description=(
                "Different pages quote different cut-off times. Buyers under "
                "time pressure abandon when they can't tell which one is real."
            ),
            sides=sides,
        )
    return None


def detect_free_delivery_conflict(crawl: CrawlResult) -> Conflict | None:
    has_no_min: list[ConflictSide] = []
    has_threshold: list[ConflictSide] = []

    for p in crawl.pages:
        if not p.ok or not p.text:
            continue
        # Look near any "free delivery / free shipping" mention
        for fd in FREE_DELIVERY_RE.finditer(p.text):
            window_start = max(0, fd.start() - 120)
            window_end = min(len(p.text), fd.end() + 120)
            window = p.text[window_start:window_end]
            side_template = ConflictSide(
                page_url=p.final_url or p.url,
                page_intent=p.intent,
                value="",
                snippet=window.replace("\n", " ").strip(),
            )
            no_min_m = NO_MIN_RE.search(window)
            thresh_m = MIN_THRESHOLD_RE.search(window)
            if no_min_m:
                side = ConflictSide(
                    **{**side_template.__dict__, "value": "Free, no minimum"}
                )
                has_no_min.append(side)
            if thresh_m:
                side = ConflictSide(
                    **{
                        **side_template.__dict__,
                        "value": f"Free above {thresh_m.group(1).strip()}",
                    }
                )
                has_threshold.append(side)

    if has_no_min and has_threshold:
        return Conflict(
            topic="Free-delivery condition",
            description=(
                "Some pages promise free delivery with no minimum, while others "
                "set a minimum order value. Buyers feel misled when they reach "
                "checkout."
            ),
            sides=[has_no_min[0], has_threshold[0]],
        )
    return None


def detect_service_area_conflict(crawl: CrawlResult) -> Conflict | None:
    by_value: dict[str, list[ConflictSide]] = {}
    for p in crawl.pages:
        if not p.ok or not p.text:
            continue
        for val, snippet in _extract_simple(p, AREA_RE):
            v = re.sub(r"\s+", " ", val).strip().rstrip(".,;")
            key = v.lower()
            by_value.setdefault(key, []).append(
                ConflictSide(
                    page_url=p.final_url or p.url,
                    page_intent=p.intent,
                    value=v,
                    snippet=snippet,
                )
            )

    distinct = list(by_value.keys())
    if len(distinct) >= 2:
        sides = [by_value[k][0] for k in distinct[:2]]
        return Conflict(
            topic="Service area / coverage",
            description=(
                "Different pages describe the delivery coverage differently. "
                "Buyers outside the named area may leave without ordering."
            ),
            sides=sides,
        )
    return None


def detect_hours_conflict(crawl: CrawlResult) -> Conflict | None:
    by_value: dict[str, list[ConflictSide]] = {}
    for p in crawl.pages:
        if not p.ok or not p.text:
            continue
        for val, snippet in _extract_simple(p, HOURS_RE):
            key = re.sub(r"\s+", "", val.lower())
            by_value.setdefault(key, []).append(
                ConflictSide(
                    page_url=p.final_url or p.url,
                    page_intent=p.intent,
                    value=val,
                    snippet=snippet,
                )
            )
    if len(by_value) >= 2:
        sides = [v[0] for v in list(by_value.values())[:2]]
        return Conflict(
            topic="Business / operating hours",
            description=(
                "Pages disagree on opening hours. This erodes trust and creates "
                "support tickets."
            ),
            sides=sides,
        )
    return None


def run_consistency_check(crawl: CrawlResult) -> list[Conflict]:
    out: list[Conflict] = []
    for fn in (
        detect_cutoff_conflicts,
        detect_free_delivery_conflict,
        detect_service_area_conflict,
        detect_hours_conflict,
    ):
        try:
            c = fn(crawl)
            if c:
                out.append(c)
        except Exception:
            continue
    return out
