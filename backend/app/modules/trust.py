"""
Module A — Hard Trust Scan.

Pure-Python checks against the CrawlResult. Emits a list of TrustCheck items
with status pass | weak | missing, a short note and an evidence snippet.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..crawler import CrawlResult, FetchedPage


@dataclass
class TrustCheck:
    key: str
    name: str
    status: str  # "pass" | "weak" | "missing"
    note: str
    evidence: str = ""


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# International phone pattern — tolerant: +, digits, spaces, dashes, parens
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?){2,4}\d{2,4}")
WHATSAPP_LINK_RE = re.compile(r"(?:wa\.me|api\.whatsapp\.com|web\.whatsapp\.com)/[+\d]+", re.I)
WHATSAPP_TEXT_RE = re.compile(r"whats[\s\-]?app", re.I)

# Common company-number / registration patterns across regions
REG_PATTERNS = [
    # Malaysia: 12 digits + optional dash + 6-digit suffix etc.
    re.compile(r"\b(?:Reg(?:istration)?\.?|Co\.?\s*No\.?|Company\s*(?:No|Number)\.?)[\s:]*([A-Z0-9\-]{6,})", re.I),
    # UK: "Company No. 12345678"
    re.compile(r"\bCompany\s*(?:Number|No\.?)\s*[:#]?\s*([0-9]{6,10})", re.I),
    # US EIN / generic tax id
    re.compile(r"\bEIN[:\s]*([0-9\-]{9,})", re.I),
    # Singapore UEN, AU ABN — generic alnum
    re.compile(r"\b(?:UEN|ABN)[:\s]*([A-Z0-9]{8,})", re.I),
]

CERT_KEYWORDS = [
    "iso 9001", "iso 27001", "iso27001", "iso 14001",
    "gdpr", "ccpa", "hipaa", "pci dss", "pci-dss",
    "soc 2", "soc2", "halal", "jakim", "haccp",
    "fda registered", "ce certified", "rohs",
    "trustpilot", "bbb accredited",
]

ADDRESS_HINT_RE = re.compile(
    r"\b\d{1,5}[A-Z]?\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*"  # 12 Main Street
    r"|\b(?:suite|ste|unit|floor|fl\.?|level|lot)\s+\d+",  # Suite 200
    re.I,
)
POSTCODE_HINT_RE = re.compile(r"\b\d{4,6}(?:[\-\s]\d{4})?\b")


def _evidence(text: str, match: str, span: int = 60) -> str:
    if not match or not text:
        return ""
    idx = text.lower().find(match.lower())
    if idx == -1:
        return match[:200]
    start = max(0, idx - span)
    end = min(len(text), idx + len(match) + span)
    snippet = text[start:end].replace("\n", " ").strip()
    return ("…" if start > 0 else "") + snippet + ("…" if end < len(text) else "")


def _join_text(pages: list[FetchedPage]) -> str:
    return "\n\n".join(p.text for p in pages if p.ok and p.text)


def check_ssl(crawl: CrawlResult) -> TrustCheck:
    if crawl.ssl_ok:
        return TrustCheck(
            key="ssl",
            name="Valid SSL certificate (HTTPS)",
            status="pass",
            note="Site is served over HTTPS.",
            evidence=crawl.base_url,
        )
    return TrustCheck(
        key="ssl",
        name="Valid SSL certificate (HTTPS)",
        status="missing",
        note="The site is not served over HTTPS — modern browsers warn users.",
        evidence=crawl.base_url,
    )


def check_registered_entity(crawl: CrawlResult) -> TrustCheck:
    text = _join_text(crawl.pages)
    for pat in REG_PATTERNS:
        m = pat.search(text)
        if m:
            return TrustCheck(
                key="entity",
                name="Registered legal entity",
                status="pass",
                note="A company registration number is published on the site.",
                evidence=_evidence(text, m.group(0)),
            )
    # Weak fallback — mentions of Ltd / LLC / Sdn Bhd / Inc / GmbH etc.
    weak = re.search(
        r"\b(?:Ltd\.?|LLC|Inc\.?|Sdn\s*Bhd|GmbH|Pte\.?\s*Ltd|S\.A\.|Co\.?,?\s*Ltd)\b",
        text,
        re.I,
    )
    if weak:
        return TrustCheck(
            key="entity",
            name="Registered legal entity",
            status="weak",
            note="Legal entity suffix detected, but no registration number.",
            evidence=_evidence(text, weak.group(0)),
        )
    return TrustCheck(
        key="entity",
        name="Registered legal entity",
        status="missing",
        note="No company name or registration number found on the site.",
    )


def check_physical_address(crawl: CrawlResult) -> TrustCheck:
    # Prefer contact / about pages
    candidates: list[FetchedPage] = []
    for intent in ("contact", "about", "home"):
        p = crawl.page_by_intent(intent)
        if p:
            candidates.append(p)
    text_blob = "\n".join(p.text for p in candidates if p.ok and p.text)
    if not text_blob:
        text_blob = _join_text(crawl.pages)

    addr_m = ADDRESS_HINT_RE.search(text_blob)
    post_m = POSTCODE_HINT_RE.search(text_blob)

    if addr_m and post_m:
        return TrustCheck(
            key="address",
            name="Physical address",
            status="pass",
            note="A street address with postal code appears on the site.",
            evidence=_evidence(text_blob, addr_m.group(0)),
        )
    if addr_m or post_m:
        hit = (addr_m or post_m).group(0)
        return TrustCheck(
            key="address",
            name="Physical address",
            status="weak",
            note="A partial address was found but not a full one with postal code.",
            evidence=_evidence(text_blob, hit),
        )
    return TrustCheck(
        key="address",
        name="Physical address",
        status="missing",
        note="No physical address is published.",
    )


def check_contact_channels(crawl: CrawlResult) -> TrustCheck:
    text = _join_text(crawl.pages)
    html_blob = "\n".join(p.html for p in crawl.pages if p.ok)
    channels: list[str] = []
    evidence_hits: list[str] = []

    email_m = EMAIL_RE.search(text)
    if email_m:
        channels.append("email")
        evidence_hits.append(email_m.group(0))

    # tel: links are the most reliable phone signal
    tel_m = re.search(r"tel:([+\d\-\s\(\)]{6,})", html_blob, re.I)
    if tel_m:
        channels.append("phone")
        evidence_hits.append(f"tel:{tel_m.group(1).strip()}")
    else:
        phone_m = PHONE_RE.search(text)
        # Cheap guard against pure dates / years matching the loose phone regex
        if phone_m and sum(c.isdigit() for c in phone_m.group(0)) >= 7:
            channels.append("phone")
            evidence_hits.append(phone_m.group(0))

    if WHATSAPP_LINK_RE.search(html_blob) or WHATSAPP_TEXT_RE.search(text):
        channels.append("WhatsApp")

    if len(channels) >= 2:
        return TrustCheck(
            key="contact",
            name="Direct human contact channels",
            status="pass",
            note=f"{', '.join(channels)} all published.",
            evidence=" · ".join(evidence_hits[:2]),
        )
    if channels:
        return TrustCheck(
            key="contact",
            name="Direct human contact channels",
            status="weak",
            note=f"Only one channel found ({channels[0]}). Add at least one more.",
            evidence=evidence_hits[0] if evidence_hits else "",
        )
    return TrustCheck(
        key="contact",
        name="Direct human contact channels",
        status="missing",
        note="No email, phone or WhatsApp contact is visible.",
    )


def check_certifications(crawl: CrawlResult) -> TrustCheck:
    text = _join_text(crawl.pages).lower()
    hits = [kw for kw in CERT_KEYWORDS if kw in text]
    if hits:
        return TrustCheck(
            key="cert",
            name="Industry certification or trust seal",
            status="pass",
            note=f"Found: {', '.join(hits[:4])}.",
            evidence=_evidence(text, hits[0]),
        )
    return TrustCheck(
        key="cert",
        name="Industry certification or trust seal",
        status="missing",
        note="No recognised certification or trust seal detected.",
    )


def check_privacy_policy(crawl: CrawlResult) -> TrustCheck:
    policy = crawl.page_by_intent("policy")
    if policy and policy.ok:
        return TrustCheck(
            key="privacy",
            name="Privacy / terms policy",
            status="pass",
            note="A privacy / terms page is published.",
            evidence=policy.final_url or policy.url,
        )
    # last resort — link text scan
    html_blob = "\n".join(p.html for p in crawl.pages if p.ok).lower()
    if "privacy" in html_blob or "terms" in html_blob:
        return TrustCheck(
            key="privacy",
            name="Privacy / terms policy",
            status="weak",
            note="A privacy/terms link exists but the page could not be reached.",
        )
    return TrustCheck(
        key="privacy",
        name="Privacy / terms policy",
        status="missing",
        note="No privacy or terms page detected.",
    )


def check_reviews(crawl: CrawlResult) -> TrustCheck:
    text = _join_text(crawl.pages).lower()
    keywords = [
        "testimonial", "customer review", "what our customers say",
        "5-star", "rated", "verified buyer", "trustpilot",
    ]
    hits = [k for k in keywords if k in text]
    if hits:
        return TrustCheck(
            key="reviews",
            name="Visible customer reviews",
            status="pass",
            note=f"Social proof present ({hits[0]}).",
        )
    if "review" in text:
        return TrustCheck(
            key="reviews",
            name="Visible customer reviews",
            status="weak",
            note="The word 'review' appears, but no clear testimonials block was detected.",
        )
    return TrustCheck(
        key="reviews",
        name="Visible customer reviews",
        status="missing",
        note="No customer ratings or testimonials surfaced on key pages.",
    )


def run_trust_scan(crawl: CrawlResult) -> list[TrustCheck]:
    """Runs every check; an exception in one must not break the others."""
    checks: list[TrustCheck] = []
    for fn in (
        check_ssl,
        check_registered_entity,
        check_physical_address,
        check_contact_channels,
        check_certifications,
        check_privacy_policy,
        check_reviews,
    ):
        try:
            checks.append(fn(crawl))
        except Exception as e:
            checks.append(
                TrustCheck(
                    key=fn.__name__,
                    name=fn.__name__.replace("check_", "").replace("_", " ").title(),
                    status="missing",
                    note=f"Internal check error: {type(e).__name__}",
                )
            )
    return checks
