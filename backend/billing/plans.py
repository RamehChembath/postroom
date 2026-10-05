"""
Plan tiers. Two currencies on purpose: what you charge the customer (INR,
via Stripe) and what Claude/OpenAI charge you per avatar (USD) are separate
things — the AI budget controls your own costs regardless of what you bill.

PRICING IS ILLUSTRATIVE — the token-cost constants in aiengine/providers.py
must be checked against Anthropic's and OpenAI's current published pricing
before this is used for real billing; they change over time.
"""
from django.conf import settings

PLANS = {
    "free": {
        "name": "Free",
        "price_monthly_inr": 0,
        "included_workspaces": 1,
        "max_workspaces": 1,
        "extra_workspace_price_inr": None,  # no additions possible
        "ai_enabled": False,
        "ai_budget_usd_per_workspace": 0,
        "stripe_price_id": None,
        "stripe_extra_avatar_price_id": None,
    },
    "base": {
        "name": "Base",
        "price_monthly_inr": 99,
        "included_workspaces": 1,
        "max_workspaces": 1,  # hard cap — no add-ons on Base; upgrade to Pro for more
        "extra_workspace_price_inr": None,
        "ai_enabled": True,
        "ai_budget_usd_per_workspace": 3,
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_BASE", ""),
        "stripe_extra_avatar_price_id": None,
    },
    "pro": {
        "name": "Pro",
        "price_monthly_inr": 199,
        "included_workspaces": 1,
        "max_workspaces": 20,
        "extra_workspace_price_inr": 100,  # per avatar beyond the first, billed as a separate Stripe line item
        "ai_enabled": True,
        "ai_budget_usd_per_workspace": 3,
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_PRO", ""),
        "stripe_extra_avatar_price_id": getattr(settings, "STRIPE_PRICE_PRO_EXTRA_AVATAR", ""),
    },
}

# Maps a Stripe price id back to the plan it represents — only the BASE price
# of each plan, never the extra-avatar add-on price (that's not plan-defining).
PRICE_ID_TO_PLAN = {p["stripe_price_id"]: key for key, p in PLANS.items() if p["stripe_price_id"]}


def plan_for_price_id(price_id):
    return PRICE_ID_TO_PLAN.get(price_id)
