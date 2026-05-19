"""Pydantic request / response schemas for the API."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# -------------------------- request models -------------------------- #


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=3, description="Website URL to audit")
    monthly_visitors: Optional[int] = Field(
        default=5000, ge=0, le=10_000_000,
        description="Owner-supplied monthly visitor estimate"
    )
    avg_order_value: Optional[float] = Field(
        default=200.0, ge=0, le=1_000_000,
        description="Average order value in USD"
    )


# -------------------------- response models ------------------------- #


class TrustCheckOut(BaseModel):
    key: str
    name: str
    status: Literal["pass", "weak", "missing"]
    note: str
    evidence: str = ""


class ConflictSideOut(BaseModel):
    page_url: str
    page_intent: str
    value: str
    snippet: str


class ConflictOut(BaseModel):
    topic: str
    description: str
    sides: list[ConflictSideOut]


class FormFieldOut(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    is_essential: bool
    reason: str


class FormFindingOut(BaseModel):
    page_url: str
    page_intent: str
    total_fields: int
    required_fields: int
    essential_required: int
    extra_required: int
    fields: list[FormFieldOut]


class FormAuditOut(BaseModel):
    forms: list[FormFindingOut]
    monthly_visitors: int
    form_reach_rate: float
    avg_order_value: float
    per_field_drop: float
    extra_required_total: int
    estimated_monthly_loss_usd: float
    notes: list[str]


class PagesSummary(BaseModel):
    fetched: int
    failed: int
    urls: list[str]


class ScoreBreakdown(BaseModel):
    trust: float
    consistency: float
    form: float


class AnalyzeResponse(BaseModel):
    ok: bool
    url: str
    base_url: str
    fetched_pages: PagesSummary
    teaser_score: int
    teaser_loss_usd: float
    teaser_locked: bool
    score: Optional[int] = None  # only set when unlocked
    score_breakdown: Optional[ScoreBreakdown] = None
    trust: list[TrustCheckOut]
    conflicts_count: int
    conflicts: Optional[list[ConflictOut]] = None  # locked behind paywall
    forms_summary: dict
    forms: Optional[FormAuditOut] = None  # locked behind paywall
    actions: list[dict]
    error: str = ""


class CheckoutRequest(BaseModel):
    report_id: Optional[str] = None
    url: Optional[str] = None  # for receipt context


class CheckoutResponse(BaseModel):
    ok: bool
    url: str = ""
    enabled: bool = False
    error: str = ""
