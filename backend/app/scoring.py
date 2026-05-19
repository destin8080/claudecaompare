"""
Score the audit on a 0-100 scale.

Weights are intentional and disclosed in the report:
  - Trust scan        : 50 pts
  - Consistency       : 30 pts (subtract for each conflict)
  - Form friction     : 20 pts (subtract per extra required field)
"""
from __future__ import annotations

from .modules.trust import TrustCheck
from .modules.consistency import Conflict
from .modules.forms import FormAudit


TRUST_POINTS = {"pass": 1.0, "weak": 0.5, "missing": 0.0}


def compute_score(
    trust: list[TrustCheck],
    conflicts: list[Conflict],
    forms: FormAudit,
) -> tuple[int, dict[str, float]]:
    """Returns (final_score, breakdown_dict)."""
    # Trust portion — 50 pts
    if trust:
        gained = sum(TRUST_POINTS.get(t.status, 0.0) for t in trust)
        trust_score = round(50 * gained / len(trust), 1)
    else:
        trust_score = 0.0

    # Consistency portion — start at 30, lose 8 per conflict
    consistency_score = max(0.0, 30.0 - 8.0 * len(conflicts))

    # Form portion — start at 20, lose 4 per extra required field
    form_score = max(0.0, 20.0 - 4.0 * forms.extra_required_total)

    total = round(trust_score + consistency_score + form_score)
    total = max(0, min(100, total))

    return total, {
        "trust": trust_score,
        "consistency": consistency_score,
        "form": form_score,
    }


def teaser_score(real_score: int) -> int:
    """
    Free-preview score shown before payment. We deliberately understate by
    a fixed margin (capped) to encourage unlock. We never push below 35
    so the report doesn't feel insulting.
    """
    margin = 18 if real_score >= 60 else 12
    return max(35, real_score - margin)
