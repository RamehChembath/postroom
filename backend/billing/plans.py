"""
Plan tiers — editable at runtime from Settings -> Plan Builder (backed by the
PlanConfig model), not hardcoded. The dict below is only the one-time seed
used the first time the app runs (so a fresh install has sensible defaults);
after that, the database is the source of truth.

Two currencies on purpose: what you charge the customer (INR, via Stripe) and
what Claude/OpenAI charge you per avatar (USD) are separate things — the AI
budget controls your own costs regardless of what you bill.
"""
from django.conf import settings

SEED_PLANS = {
    "free": {
        "name": "Free", "order": 0, "price_monthly_inr": 0,
        "included_workspaces": 1, "max_workspaces": 1, "extra_workspace_price_inr": None,
        "ai_enabled": False, "ai_budget_usd_per_workspace": 0,
        "stripe_price_id": "", "stripe_extra_avatar_price_id": "",
    },
    "base": {
        "name": "Base", "order": 1, "price_monthly_inr": 99,
        "included_workspaces": 1, "max_workspaces": 1, "extra_workspace_price_inr": None,
        "ai_enabled": True, "ai_budget_usd_per_workspace": 3,
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_BASE", ""), "stripe_extra_avatar_price_id": "",
    },
    "pro": {
        "name": "Pro", "order": 2, "price_monthly_inr": 199,
        "included_workspaces": 1, "max_workspaces": 20, "extra_workspace_price_inr": 100,
        "ai_enabled": True, "ai_budget_usd_per_workspace": 3,
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_PRO", ""),
        "stripe_extra_avatar_price_id": getattr(settings, "STRIPE_PRICE_PRO_EXTRA_AVATAR", ""),
    },
}


def _ensure_seeded():
    from .models import PlanConfig
    if PlanConfig.objects.exists():
        return
    for key, data in SEED_PLANS.items():
        PlanConfig.objects.create(key=key, **data)


def get_plans() -> dict:
    """Returns the same shape the rest of the app has always used:
    {"free": {...}, "base": {...}, "pro": {...}}, now read from the database."""
    from .models import PlanConfig
    _ensure_seeded()
    plans = {}
    for p in PlanConfig.objects.all():
        plans[p.key] = {
            "name": p.name, "price_monthly_inr": p.price_monthly_inr,
            "included_workspaces": p.included_workspaces, "max_workspaces": p.max_workspaces,
            "extra_workspace_price_inr": p.extra_workspace_price_inr,
            "ai_enabled": p.ai_enabled, "ai_budget_usd_per_workspace": float(p.ai_budget_usd_per_workspace),
            "stripe_price_id": p.stripe_price_id, "stripe_extra_avatar_price_id": p.stripe_extra_avatar_price_id,
        }
    return plans


def plan_for_price_id(price_id):
    if not price_id:
        return None
    for key, plan in get_plans().items():
        if plan["stripe_price_id"] == price_id:
            return key
    return None
