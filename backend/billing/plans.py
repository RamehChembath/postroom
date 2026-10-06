"""
Plans are fully dynamic now — created/edited/deleted from Settings -> Plan
Builder, backed by PlanConfig + Feature + PlanFeature. Everything below is
only the ONE-TIME seed data used the first time the app runs, so a fresh
install starts with three sensible example plans instead of nothing.
"""
from django.conf import settings

SEED_PLANS = {
    "free": {
        "name": "Free", "order": 0, "price_monthly_inr": 0,
        "included_workspaces": 1, "max_workspaces": 1, "extra_workspace_price_inr": None,
        "ai_budget_usd_per_workspace": 0, "is_default_free": True,
        "stripe_price_id": "", "stripe_extra_avatar_price_id": "",
    },
    "base": {
        "name": "Base", "order": 1, "price_monthly_inr": 99,
        "included_workspaces": 1, "max_workspaces": 1, "extra_workspace_price_inr": None,
        "ai_budget_usd_per_workspace": 3, "is_default_free": False,
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_BASE", ""), "stripe_extra_avatar_price_id": "",
    },
    "pro": {
        "name": "Pro", "order": 2, "price_monthly_inr": 199,
        "included_workspaces": 1, "max_workspaces": 20, "extra_workspace_price_inr": 100,
        "ai_budget_usd_per_workspace": 3, "is_default_free": False,
        "stripe_price_id": getattr(settings, "STRIPE_PRICE_PRO", ""),
        "stripe_extra_avatar_price_id": getattr(settings, "STRIPE_PRICE_PRO_EXTRA_AVATAR", ""),
    },
}

# key: (name, category, value_kind, unit, tier_options, description)
SEED_FEATURES = {
    "draft_generation":        ("Post & article drafts", "ai", "quantity", "posts/month", [], "AI-written posts and articles."),
    "reply_suggestions":       ("Reply suggestions", "ai", "quantity", "replies/month", [], "AI-drafted replies to comments you log."),
    "calendar_builder":        ("Calendar builder", "ai", "quantity", "items/month", [], "AI-built posting calendar: titles + dates."),
    "topic_suggestions":       ("Topic suggestions", "ai", "quantity", "suggestions/month", [], "AI content ideas based on audience & industry."),
    "image_generation":        ("Image generation", "ai", "quantity", "images/month", [], "AI images attached to posts."),
    "growth_analysis":         ("Growth analysis", "ai", "quantity", "analyses/month", [], "AI summary of performance trends on the dashboard."),
    "tone_analysis":           ("Tone analysis", "ai", "quantity", "analyses/month", [], "Learns voice from the user's posted content."),
    "smart_day_scheduling":    ("Smart day scheduling", "ai", "boolean", "", [], "Calendar builder reasons about best/worst posting days, not just spacing."),
    "future_planning_horizon": ("Future planning horizon", "ai", "tier", "", ["none", "1_month", "3_months"], "How far ahead topic/next-step suggestions look."),
    "multi_avatar":            ("Multiple avatars", "non_ai", "boolean", "", [], "Allowed more than one avatar at all (separate from the max-avatars number)."),
    "email_reminders":         ("Email reminders", "non_ai", "boolean", "", [], "Daily email when a post in the Posting Room is due."),
    "goals_tracking":          ("Goals tracking", "non_ai", "boolean", "", [], "Set and track progress against a goal."),
    "manual_post_logging":     ("Manual post logging", "non_ai", "boolean", "", [], "Paste/log your own posts to track likes & comments — works with zero AI."),
}

# plan_key -> {feature_key: (enabled, quantity_or_None, tier_or_"")}
SEED_PLAN_FEATURES = {
    "free": {
        "draft_generation": (False, 0, ""), "reply_suggestions": (False, 0, ""),
        "calendar_builder": (False, 0, ""), "topic_suggestions": (False, 0, ""),
        "image_generation": (False, 0, ""), "growth_analysis": (False, 0, ""),
        "tone_analysis": (False, 0, ""), "smart_day_scheduling": (False, None, ""),
        "future_planning_horizon": (True, None, "none"), "multi_avatar": (False, None, ""),
        "email_reminders": (False, None, ""), "goals_tracking": (False, None, ""),
        "manual_post_logging": (True, None, ""),
    },
    "base": {
        "draft_generation": (True, 10, ""), "reply_suggestions": (True, 15, ""),
        "calendar_builder": (True, 3, ""), "topic_suggestions": (True, 5, ""),
        "image_generation": (False, 0, ""), "growth_analysis": (True, 2, ""),
        "tone_analysis": (True, 2, ""), "smart_day_scheduling": (False, None, ""),
        "future_planning_horizon": (True, None, "1_month"), "multi_avatar": (False, None, ""),
        "email_reminders": (True, None, ""), "goals_tracking": (True, None, ""),
        "manual_post_logging": (True, None, ""),
    },
    "pro": {
        "draft_generation": (True, 40, ""), "reply_suggestions": (True, 60, ""),
        "calendar_builder": (True, 15, ""), "topic_suggestions": (True, 20, ""),
        "image_generation": (True, 10, ""), "growth_analysis": (True, 10, ""),
        "tone_analysis": (True, 10, ""), "smart_day_scheduling": (True, None, ""),
        "future_planning_horizon": (True, None, "3_months"), "multi_avatar": (True, None, ""),
        "email_reminders": (True, None, ""), "goals_tracking": (True, None, ""),
        "manual_post_logging": (True, None, ""),
    },
}


def _ensure_seeded():
    from .models import PlanConfig, Feature, PlanFeature
    if not Feature.objects.exists():
        for key, (name, category, kind, unit, tier_opts, desc) in SEED_FEATURES.items():
            Feature.objects.create(key=key, name=name, category=category, value_kind=kind,
                                    unit=unit, tier_options=tier_opts, description=desc,
                                    order=list(SEED_FEATURES.keys()).index(key))
    if not PlanConfig.objects.exists():
        for key, data in SEED_PLANS.items():
            plan = PlanConfig.objects.create(key=key, **data)
            for fkey, (enabled, qty, tier) in SEED_PLAN_FEATURES.get(key, {}).items():
                feature = Feature.objects.filter(key=fkey).first()
                if feature:
                    PlanFeature.objects.create(plan=plan, feature=feature, enabled=enabled, quantity=qty, tier=tier)


def get_plans() -> dict:
    """Same shape the rest of the app has always used: {"free": {...}, ...},
    now read from the database and including every plan that exists, however
    many there are."""
    from .models import PlanConfig
    _ensure_seeded()
    plans = {}
    for p in PlanConfig.objects.all():
        plans[p.key] = {
            "name": p.name, "price_monthly_inr": p.price_monthly_inr,
            "included_workspaces": p.included_workspaces, "max_workspaces": p.max_workspaces,
            "extra_workspace_price_inr": p.extra_workspace_price_inr,
            "ai_budget_usd_per_workspace": float(p.ai_budget_usd_per_workspace),
            "stripe_price_id": p.stripe_price_id, "stripe_extra_avatar_price_id": p.stripe_extra_avatar_price_id,
            "is_default_free": p.is_default_free,
        }
    return plans


def default_free_plan_key() -> str:
    from .models import PlanConfig
    _ensure_seeded()
    p = PlanConfig.objects.filter(is_default_free=True).first() or PlanConfig.objects.order_by("order").first()
    return p.key if p else "free"


def plan_for_price_id(price_id):
    if not price_id:
        return None
    for key, plan in get_plans().items():
        if plan["stripe_price_id"] == price_id:
            return key
    return None
