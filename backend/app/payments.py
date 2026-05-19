"""
Stripe checkout — test mode by default.

If STRIPE_SECRET_KEY is not configured, the API returns enabled=false so the
frontend can show a "Payments not configured" notice instead of failing.
"""
from __future__ import annotations

import stripe

from .config import settings


def create_unlock_session(success_url: str, cancel_url: str, url_ctx: str = "") -> dict:
    if not settings.stripe_enabled:
        return {"ok": False, "enabled": False, "url": "", "error": "Stripe not configured"}

    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": settings.UNLOCK_PRICE_CENTS,
                        "product_data": {
                            "name": "Compare Your Website — Full Audit Unlock",
                            "description": (
                                f"Unlocks the full report for {url_ctx or 'your site'}: "
                                "real 0-100 score, every conflict found, the form-friction "
                                "audit and the action plan."
                            ),
                        },
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            automatic_tax={"enabled": False},
            payment_method_types=["card"],
            billing_address_collection="auto",
            allow_promotion_codes=True,
        )
        return {"ok": True, "enabled": True, "url": session.url or "", "error": ""}
    except Exception as e:
        return {
            "ok": False,
            "enabled": True,
            "url": "",
            "error": f"{type(e).__name__}: {e}",
        }
