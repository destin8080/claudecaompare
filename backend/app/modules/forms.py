"""
Module C — Form friction analysis.

Locate inquiry / contact / quote forms on crawled pages, count required vs
unnecessary fields, and estimate revenue lost to over-asking using the
public formula:

    estimated_loss = (extra_required_fields × per-field abandonment rate)
                      × monthly_visitors × form_reach_rate × avg_order_value

The two rates default to industry benchmarks; callers can override.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from ..crawler import CrawlResult, FetchedPage


@dataclass
class FormField:
    name: str
    label: str
    type: str  # input type
    required: bool
    is_essential: bool  # "you actually need this to do business"
    reason: str  # explanation tag


@dataclass
class FormFinding:
    page_url: str
    page_intent: str
    total_fields: int
    required_fields: int
    essential_required: int
    extra_required: int
    fields: list[FormField]


@dataclass
class FormAudit:
    forms: list[FormFinding] = field(default_factory=list)
    # Inputs to the loss model
    monthly_visitors: int = 5000
    form_reach_rate: float = 0.12  # share of visitors who see/start a form
    avg_order_value: float = 200.0  # USD
    per_field_drop: float = 0.07  # 7% drop per extra required field (Baymard-style)
    # Outputs
    extra_required_total: int = 0
    estimated_monthly_loss_usd: float = 0.0
    notes: list[str] = field(default_factory=list)


# Fields we consider essential for an inquiry / contact / quote form.
# Anything else marked `required` is "extra required".
ESSENTIAL_KEYS = {
    "name", "full_name", "first_name", "last_name",
    "email", "e-mail", "mail",
    "phone", "tel", "telephone", "mobile", "whatsapp",
    "message", "enquiry", "inquiry", "question", "details", "comments",
    "company",  # B2B inquiries — company is usually essential
}

# Patterns that mark a field as "unnecessary" friction
NOISY_KEYS = {
    "fax", "title", "salutation", "gender", "dob", "date_of_birth", "age",
    "industry", "annual_revenue", "company_size", "team_size", "budget",
    "how_did_you_hear", "referral", "source", "hear_about",
    "address_line_2", "secondary_address", "linkedin", "twitter", "website",
    "department", "job_title", "role", "country", "state", "city", "zip", "postal",
}


def _clean_key(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s


def _classify(name: str, label: str, type_: str) -> tuple[bool, str]:
    """Return (is_essential, reason)."""
    if type_ in {"hidden", "submit", "button", "reset"}:
        return True, "system field"
    key_candidates = {_clean_key(name), _clean_key(label)}
    for k in key_candidates:
        if not k:
            continue
        if k in ESSENTIAL_KEYS:
            return True, f"essential ({k})"
        if any(ess in k for ess in ESSENTIAL_KEYS):
            return True, "essential"
        if k in NOISY_KEYS or any(noise in k for noise in NOISY_KEYS):
            return False, f"unnecessary ({k})"
    # consent / privacy checkboxes are essential by law in many regions
    if type_ == "checkbox" and any(
        w in (label.lower() + " " + name.lower())
        for w in ("agree", "consent", "privacy", "terms", "gdpr")
    ):
        return True, "legal consent"
    return False, "unclassified"


def _extract_label(form_soup, input_tag) -> str:
    # label by for=
    tag_id = input_tag.get("id")
    if tag_id:
        lab = form_soup.find("label", attrs={"for": tag_id})
        if lab and lab.get_text(strip=True):
            return lab.get_text(" ", strip=True)
    # wrapping label
    parent = input_tag.find_parent("label")
    if parent and parent.get_text(strip=True):
        return parent.get_text(" ", strip=True)
    # placeholder fallback
    return (input_tag.get("placeholder") or input_tag.get("aria-label") or "").strip()


def _analyze_form(form_soup, page: FetchedPage) -> FormFinding | None:
    inputs = form_soup.find_all(["input", "textarea", "select"])
    if not inputs:
        return None

    fields: list[FormField] = []
    for tag in inputs:
        type_ = (tag.get("type") or tag.name or "").lower()
        if type_ in {"hidden", "submit", "button", "reset", "image"}:
            continue
        name = tag.get("name") or tag.get("id") or ""
        label = _extract_label(form_soup, tag) or name
        required = tag.has_attr("required") or (
            tag.get("aria-required", "").lower() == "true"
        )
        is_essential, reason = _classify(name, label, type_)
        fields.append(
            FormField(
                name=name or label or "(unnamed)",
                label=label or name or "(no label)",
                type=type_,
                required=required,
                is_essential=is_essential,
                reason=reason,
            )
        )

    if not fields:
        return None

    required_fields = [f for f in fields if f.required]
    essential_required = sum(1 for f in required_fields if f.is_essential)
    extra_required = len(required_fields) - essential_required

    return FormFinding(
        page_url=page.final_url or page.url,
        page_intent=page.intent,
        total_fields=len(fields),
        required_fields=len(required_fields),
        essential_required=essential_required,
        extra_required=extra_required,
        fields=fields,
    )


def _form_looks_like_inquiry(form_soup) -> bool:
    blob = " ".join(
        [
            form_soup.get("id", "") or "",
            form_soup.get("class", "") if isinstance(form_soup.get("class", ""), str) else " ".join(form_soup.get("class") or []),
            form_soup.get("action", "") or "",
            form_soup.get_text(" ", strip=True)[:400],
        ]
    ).lower()
    # Avoid newsletter / search forms
    if any(w in blob for w in ("search", "newsletter", "subscribe", "login", "sign in", "signup", "register")):
        # Allow newsletter only if it also has multiple fields
        return False
    cues = ("contact", "inquiry", "enquiry", "quote", "demo", "get in touch", "message")
    if any(c in blob for c in cues):
        return True
    # if it has email + message-ish textarea, treat as inquiry
    has_email = bool(form_soup.find("input", {"type": "email"}))
    has_textarea = bool(form_soup.find("textarea"))
    return has_email and has_textarea


def run_form_audit(
    crawl: CrawlResult,
    monthly_visitors: int = 5000,
    avg_order_value: float = 200.0,
    form_reach_rate: float = 0.12,
    per_field_drop: float = 0.07,
) -> FormAudit:
    audit = FormAudit(
        monthly_visitors=monthly_visitors,
        avg_order_value=avg_order_value,
        form_reach_rate=form_reach_rate,
        per_field_drop=per_field_drop,
    )

    for page in crawl.pages:
        if not page.ok or not page.html:
            continue
        try:
            soup = BeautifulSoup(page.html, "lxml")
        except Exception:
            continue

        for form_tag in soup.find_all("form"):
            try:
                if not _form_looks_like_inquiry(form_tag):
                    continue
                finding = _analyze_form(form_tag, page)
                if finding and finding.total_fields > 0:
                    audit.forms.append(finding)
            except Exception:
                continue

    extra_total = sum(f.extra_required for f in audit.forms)
    audit.extra_required_total = extra_total

    if not audit.forms:
        audit.notes.append(
            "No inquiry / contact form was reached during the crawl. "
            "If your form is behind a login or pop-up, the audit cannot see it."
        )

    # Loss model — capped at a sane maximum.
    drop_share = min(extra_total * per_field_drop, 0.65)
    audit.estimated_monthly_loss_usd = round(
        monthly_visitors * form_reach_rate * drop_share * avg_order_value, 2
    )
    return audit
