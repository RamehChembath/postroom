"""
Two layers of enforcement, both per-workspace:
1. Per-feature quota (the one that actually drives upgrades) — e.g. "Base
   gets 10 drafts/month, Pro gets 40" — configured per plan in Settings ->
   Plan Builder, checked by check_feature_allowed() against real usage
   counted from AIUsageEvent.
2. A $ budget safety net underneath all of it, independent of which features
   are enabled — protects against any single avatar's cost blowing past a
   sane ceiling even while still within its feature quotas.
"""
from decimal import Decimal
from django.db import transaction

from .models import Subscription, WorkspaceUsage, AIUsageEvent, PlanFeature
from .plans import get_plans, default_free_plan_key


class UsageLimitExceeded(Exception):
    """A user-facing, non-retryable billing/plan limit — distinct from a provider
    failure (aiengine.providers.AIError), so views can return 402 instead of 502."""


def get_or_create_subscription(user):
    sub, _ = Subscription.objects.get_or_create(user=user, defaults={"plan": default_free_plan_key()})
    return sub


def get_or_create_current_usage(workspace):
    period_start = WorkspaceUsage.current_period_start()
    usage, _ = WorkspaceUsage.objects.get_or_create(workspace=workspace, period_start=period_start)
    return usage


def _plan_for_workspace(workspace):
    sub = get_or_create_subscription(workspace.owner)
    return sub, get_plans()[sub.plan]


def check_ai_allowed(workspace):
    """The $ budget safety net — call before any Claude/OpenAI request,
    independent of which specific feature it's for."""
    sub, plan = _plan_for_workspace(workspace)
    budget = Decimal(str(plan["ai_budget_usd_per_workspace"]))
    usage = get_or_create_current_usage(workspace)
    if budget <= 0:
        raise UsageLimitExceeded(f"AI features aren't available on the {plan['name']} plan.")
    if usage.cost_usd >= budget:
        raise UsageLimitExceeded(
            f"{workspace.name} has used its ${budget} AI budget for this month on the {plan['name']} plan. "
            f"It renews next month, or use a different avatar with budget remaining."
        )


def check_feature_allowed(workspace, feature_key):
    """The real upgrade-driving gate — is this specific feature enabled for
    this avatar's plan, and if it's quantity-limited, is there quota left
    this month? Also enforces the $ safety net (check_ai_allowed) underneath,
    so callers only need this one function. Returns the PlanFeature row
    (useful for tier-kind features — callers can read .tier)."""
    sub, _ = _plan_for_workspace(workspace)
    try:
        pf = PlanFeature.objects.select_related("feature").get(plan__key=sub.plan, feature__key=feature_key)
    except PlanFeature.DoesNotExist:
        raise UsageLimitExceeded(f"This feature isn't configured for the {sub.plan} plan.")

    if not pf.enabled:
        raise UsageLimitExceeded(f'"{pf.feature.name}" isn\'t available on your current plan. Upgrade to unlock it.')

    if pf.feature.value_kind == "quantity" and pf.quantity is not None:
        period_start = WorkspaceUsage.current_period_start()
        used = AIUsageEvent.objects.filter(workspace=workspace, purpose=feature_key, created_at__gte=period_start).count()
        if used >= pf.quantity:
            raise UsageLimitExceeded(
                f"You've used all {pf.quantity} {pf.feature.unit or 'uses'} of \"{pf.feature.name}\" this month on your plan."
            )

    check_ai_allowed(workspace)
    return pf


@transaction.atomic
def record_ai_cost(workspace, cost_usd, purpose="unknown", model=""):
    """Call after a successful Claude/OpenAI response with its real computed cost.
    Logs an individual AIUsageEvent — this is both the cost-by-purpose/model
    breakdown data AND the record check_feature_allowed() counts against each
    feature's monthly quota — AND rolls into the $ safety-net total."""
    if not cost_usd:
        return
    usage = WorkspaceUsage.objects.select_for_update().get_or_create(
        workspace=workspace, period_start=WorkspaceUsage.current_period_start()
    )[0]
    usage.cost_usd += Decimal(str(cost_usd))
    usage.save(update_fields=["cost_usd"])
    AIUsageEvent.objects.create(workspace=workspace, purpose=purpose, model=model, cost_usd=Decimal(str(cost_usd)))


def is_feature_enabled(workspace, feature_key) -> bool:
    """Read-only check for boolean/tier features that change HOW an already-
    allowed action behaves, rather than whether it's allowed at all — doesn't
    raise, doesn't count against any quota. Use check_feature_allowed() for
    actual gating; use this for reading a style flag."""
    sub, _ = _plan_for_workspace(workspace)
    return PlanFeature.objects.filter(plan__key=sub.plan, feature__key=feature_key, enabled=True).exists()


def feature_tier_value(workspace, feature_key) -> str:
    sub, _ = _plan_for_workspace(workspace)
    pf = PlanFeature.objects.filter(plan__key=sub.plan, feature__key=feature_key).first()
    return pf.tier if pf else ""


def feature_status(workspace, feature_key):
    """Used/limit for one feature, for showing progress in the UI."""
    sub, _ = _plan_for_workspace(workspace)
    try:
        pf = PlanFeature.objects.select_related("feature").get(plan__key=sub.plan, feature__key=feature_key)
    except PlanFeature.DoesNotExist:
        return {"enabled": False, "used": 0, "quantity": 0, "tier": ""}
    used = 0
    if pf.feature.value_kind == "quantity":
        period_start = WorkspaceUsage.current_period_start()
        used = AIUsageEvent.objects.filter(workspace=workspace, purpose=feature_key, created_at__gte=period_start).count()
    return {"enabled": pf.enabled, "used": used, "quantity": pf.quantity, "tier": pf.tier}


def workspace_usage_summary(workspace):
    sub, plan = _plan_for_workspace(workspace)
    usage = get_or_create_current_usage(workspace)
    budget = Decimal(str(plan["ai_budget_usd_per_workspace"]))
    return {
        "workspace_id": workspace.id, "workspace_name": workspace.name,
        "ai_enabled": budget > 0,
        "spend_usd": float(usage.cost_usd), "budget_usd": float(budget),
        "pct_used": float(min(Decimal(100), (usage.cost_usd / budget * 100))) if budget else 100.0,
    }


def account_usage_summary(user):
    """Everything the Billing page needs: plan, status, per-workspace AI spend, avatar limits."""
    sub = get_or_create_subscription(user)
    plan = get_plans()[sub.plan]
    from brand.models import Workspace
    workspaces = Workspace.objects.filter(owner=user)
    return {
        "plan": sub.plan, "plan_name": plan["name"], "status": sub.status,
        "price_monthly_inr": plan["price_monthly_inr"],
        "max_workspaces": plan["max_workspaces"], "included_workspaces": plan["included_workspaces"],
        "extra_workspace_price_inr": plan["extra_workspace_price_inr"],
        "workspace_count": workspaces.count(),
        "workspaces": [workspace_usage_summary(w) for w in workspaces],
        "current_period_end": sub.current_period_end, "cancel_at_period_end": sub.cancel_at_period_end,
    }


def _effective_max_workspaces(plan, sub):
    """A plan's numeric max_workspaces is capped at 1 unless the multi_avatar
    feature is actually enabled for it — so disabling that feature always
    wins, however the number is set."""
    try:
        pf = PlanFeature.objects.select_related("feature").get(plan__key=sub.plan, feature__key="multi_avatar")
        if not pf.enabled:
            return min(plan["max_workspaces"], 1)
    except PlanFeature.DoesNotExist:
        pass
    return plan["max_workspaces"]


def check_workspace_limit(user):
    """Call before creating a new workspace. Raises UsageLimitExceeded at the plan's cap."""
    from brand.models import Workspace
    sub = get_or_create_subscription(user)
    plan = get_plans()[sub.plan]
    max_ws = _effective_max_workspaces(plan, sub)
    count = Workspace.objects.filter(owner=user).count()
    if count >= max_ws:
        raise UsageLimitExceeded(
            f"The {plan['name']} plan allows {max_ws} {'avatar' if max_ws == 1 else 'avatars'}. Upgrade to add more."
        )


def pending_extra_avatar_cost(user):
    """What the NEXT workspace creation would add to the monthly bill, in INR —
    None if it's still within the plan's included count."""
    from brand.models import Workspace
    sub = get_or_create_subscription(user)
    plan = get_plans()[sub.plan]
    count = Workspace.objects.filter(owner=user).count()
    if count < plan["included_workspaces"]:
        return None
    return plan["extra_workspace_price_inr"]
