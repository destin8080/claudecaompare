"""
FastAPI entry point.

Endpoints:
    GET  /healthz                         — liveness
    GET  /config                          — public flags (stripe enabled, price)
    POST /analyze                         — run the full audit
    POST /checkout                        — create a Stripe Checkout session
"""
from __future__ import annotations

import asyncio
import os
import secrets
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .crawler import crawl_site
from .modules.trust import run_trust_scan, TrustCheck
from .modules.consistency import run_consistency_check
from .modules.forms import run_form_audit
from .scoring import compute_score, teaser_score
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CheckoutRequest,
    CheckoutResponse,
    ConflictOut,
    ConflictSideOut,
    FormAuditOut,
    FormFieldOut,
    FormFindingOut,
    PagesSummary,
    ScoreBreakdown,
    TrustCheckOut,
)
from .payments import create_unlock_session


app = FastAPI(title="Compare Your Website API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory cache of generated reports so the paywall can be enforced
# server-side without a DB. Keyed by report_id; expires after 1 hour.
# Each value: {"created": epoch, "url": str, "locked_payload": dict}
_REPORTS: dict[str, dict] = {}
_REPORT_TTL_SECONDS = 60 * 60


def _gc_reports() -> None:
    now = time.time()
    dead = [k for k, v in _REPORTS.items() if now - v["created"] > _REPORT_TTL_SECONDS]
    for k in dead:
        _REPORTS.pop(k, None)


# ----------------------------- routes ----------------------------- #


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "compare-your-website"}


@app.get("/config")
async def public_config():
    return {
        "stripe_enabled": settings.stripe_enabled,
        "unlock_price_cents": settings.UNLOCK_PRICE_CENTS,
        "unlock_price_display": f"${settings.UNLOCK_PRICE_CENTS / 100:.0f}",
    }


def _trust_to_out(t: TrustCheck) -> TrustCheckOut:
    return TrustCheckOut(
        key=t.key, name=t.name, status=t.status, note=t.note, evidence=t.evidence
    )


def _build_actions(
    trust: list[TrustCheck],
    conflicts_count: int,
    forms_extra: int,
) -> list[dict]:
    actions: list[dict] = []
    if conflicts_count > 0:
        actions.append(
            {
                "title": "Fix the conflicting facts across pages.",
                "when": "Today · near-zero cost",
                "detail": (
                    "Decide the single correct value for cut-off, free-delivery "
                    "rule and service area — then update every page to match."
                ),
            }
        )
    if forms_extra > 0:
        actions.append(
            {
                "title": "Remove unnecessary required fields from your inquiry form.",
                "when": "This week",
                "detail": (
                    "Each extra required field measurably lowers conversion. "
                    "Make non-essential fields optional or drop them."
                ),
            }
        )
    missing_keys = {t.key for t in trust if t.status == "missing"}
    if "cert" in missing_keys or "reviews" in missing_keys:
        actions.append(
            {
                "title": "Add social proof or a recognised certification.",
                "when": "Follow-up",
                "detail": "Testimonials, ratings or an industry seal lift confidence on first visit.",
            }
        )
    if "address" in missing_keys or "entity" in missing_keys:
        actions.append(
            {
                "title": "Publish a registered entity name and physical address.",
                "when": "This week",
                "detail": "Buyers — especially overseas — need to verify you're a real company.",
            }
        )
    if not actions:
        actions.append(
            {
                "title": "Run the audit again after launching new pages.",
                "when": "Ongoing",
                "detail": "Trust and consistency drift quickly when content changes — re-check monthly.",
            }
        )
    return actions


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, unlock: Optional[str] = None):
    """
    Run the full audit. Returns the teaser by default; pass ?unlock=<token>
    obtained after successful payment to receive the full payload.
    """
    _gc_reports()

    try:
        crawl = await crawl_site(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawler error: {e}")

    if crawl.error and not crawl.pages:
        return AnalyzeResponse(
            ok=False,
            url=req.url,
            base_url=crawl.base_url,
            fetched_pages=PagesSummary(fetched=0, failed=0, urls=[]),
            teaser_score=0,
            teaser_loss_usd=0.0,
            teaser_locked=True,
            trust=[],
            conflicts_count=0,
            forms_summary={"forms_found": 0, "extra_required_total": 0},
            actions=[],
            error=crawl.error or "Crawl failed",
        )

    # --- Run the three modules with isolated error handling ---
    try:
        trust = run_trust_scan(crawl)
    except Exception:
        trust = []

    try:
        conflicts = run_consistency_check(crawl)
    except Exception:
        conflicts = []

    try:
        form_audit = run_form_audit(
            crawl,
            monthly_visitors=req.monthly_visitors or 5000,
            avg_order_value=req.avg_order_value or 200.0,
        )
    except Exception:
        from .modules.forms import FormAudit

        form_audit = FormAudit(
            monthly_visitors=req.monthly_visitors or 5000,
            avg_order_value=req.avg_order_value or 200.0,
            notes=["Form audit could not run for this site."],
        )

    real_score, breakdown = compute_score(trust, conflicts, form_audit)
    shown_teaser_score = teaser_score(real_score)

    # Headline loss the teaser shows = form-friction loss + a small
    # conflict-driven hesitation tax (USD 800 per detected conflict, capped).
    hesitation_tax = min(len(conflicts) * 800, 4800)
    teaser_loss_total = round(form_audit.estimated_monthly_loss_usd + hesitation_tax, 2)

    fetched_ok = [p for p in crawl.pages if p.ok]
    failed = [p for p in crawl.pages if not p.ok]

    # Compose locked payload (full) and teaser payload
    conflicts_out = [
        ConflictOut(
            topic=c.topic,
            description=c.description,
            sides=[
                ConflictSideOut(
                    page_url=s.page_url,
                    page_intent=s.page_intent,
                    value=s.value,
                    snippet=s.snippet,
                )
                for s in c.sides
            ],
        )
        for c in conflicts
    ]
    forms_out = FormAuditOut(
        forms=[
            FormFindingOut(
                page_url=f.page_url,
                page_intent=f.page_intent,
                total_fields=f.total_fields,
                required_fields=f.required_fields,
                essential_required=f.essential_required,
                extra_required=f.extra_required,
                fields=[FormFieldOut(**fld.__dict__) for fld in f.fields],
            )
            for f in form_audit.forms
        ],
        monthly_visitors=form_audit.monthly_visitors,
        form_reach_rate=form_audit.form_reach_rate,
        avg_order_value=form_audit.avg_order_value,
        per_field_drop=form_audit.per_field_drop,
        extra_required_total=form_audit.extra_required_total,
        estimated_monthly_loss_usd=form_audit.estimated_monthly_loss_usd,
        notes=form_audit.notes,
    )

    actions = _build_actions(trust, len(conflicts), form_audit.extra_required_total)

    # Validate unlock token
    is_unlocked = False
    if unlock:
        rec = _REPORTS.get(unlock)
        if rec and rec.get("url") == req.url:
            is_unlocked = True

    # Stash a fresh report id for later unlock (the teaser response carries it).
    report_id = secrets.token_urlsafe(18)
    _REPORTS[report_id] = {
        "created": time.time(),
        "url": req.url,
        "paid": False,
    }

    response = AnalyzeResponse(
        ok=True,
        url=req.url,
        base_url=crawl.base_url,
        fetched_pages=PagesSummary(
            fetched=len(fetched_ok),
            failed=len(failed),
            urls=[p.final_url or p.url for p in crawl.pages],
        ),
        teaser_score=shown_teaser_score,
        teaser_loss_usd=teaser_loss_total,
        teaser_locked=not is_unlocked,
        score=real_score if is_unlocked else None,
        score_breakdown=ScoreBreakdown(**breakdown) if is_unlocked else None,
        trust=[_trust_to_out(t) for t in trust],
        conflicts_count=len(conflicts),
        conflicts=conflicts_out if is_unlocked else None,
        forms_summary={
            "forms_found": len(form_audit.forms),
            "extra_required_total": form_audit.extra_required_total,
            "estimated_monthly_loss_usd": form_audit.estimated_monthly_loss_usd,
        },
        forms=forms_out if is_unlocked else None,
        actions=actions if is_unlocked else actions[:1],  # one teaser action
        error="",
    )

    # The frontend needs the report_id to use in the checkout call; add it to
    # the forms_summary dict (it isn't sensitive).
    response.forms_summary["report_id"] = report_id
    response.forms_summary["real_score_locked"] = not is_unlocked
    return response


@app.post("/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest):
    if not settings.stripe_enabled:
        return CheckoutResponse(
            ok=False, enabled=False, url="",
            error="Stripe is not configured on the server.",
        )

    report_id = req.report_id or ""
    if report_id and report_id not in _REPORTS:
        # Allow new sessions even without a known report — useful before /analyze
        pass

    success_url = (
        f"{settings.FRONTEND_URL}/?paid=1"
        f"&rid={report_id}"
        if report_id
        else f"{settings.FRONTEND_URL}/?paid=1"
    )
    cancel_url = f"{settings.FRONTEND_URL}/?paid=0"

    out = create_unlock_session(success_url, cancel_url, url_ctx=req.url or "")
    if out["ok"] and report_id and report_id in _REPORTS:
        _REPORTS[report_id]["paid"] = True  # test-mode shortcut: trust the return
    return CheckoutResponse(
        ok=out["ok"], enabled=out["enabled"], url=out["url"], error=out["error"]
    )
