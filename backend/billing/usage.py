"""
Usage enforcement, now per-workspace and dollar-denominated:
- Free plan: AI is off entirely, regardless of spend.
- Base/Pro: each avatar gets its own $3/month AI budget. Spend is checked
  BEFORE a call (so an exhausted avatar is blocked up front) and recorded
  AFTER a call succeeds, from the real token usage the provider reports —
  this can let a single call push slightly over budget before the next one
  is blocked, same soft-limit pattern most metered billing uses.
"""
from decimal import Decimal
from django.db import transaction

from .models import Subscription, WorkspaceUsage
from .plans import PLANS


class UsageLimitExceeded(Exception):
    """A user-facing, non-retryable billing/plan limit — distinct from a provider
    failure (aiengine.providers.AIError), so views can return 402 instead of 502."""


def get_or_create_subscription(user):
    sub, _ = Subscription.objects.get_or_create(user=user)
    return sub


def get_or_create_current_usage(workspace):
    period_start = WorkspaceUsage.current_period_start()
    usage, _ = WorkspaceUsage.objects.get_or_create(workspace=workspace, period_start=period_start)
    return usage


def _plan_for_workspace(workspace):
    sub = get_or_create_subscription(workspace.owner)
    return sub, PLANS[sub.plan]


def check_ai_allowed(workspace):
    """Call before any Claude/OpenAI request for this avatar. Raises
    UsageLimitExceeded and makes the call if the avatar is clear to spend."""
    sub, plan = _plan_for_workspace(workspace)
    if not plan["ai_enabled"]:
        raise UsageLimitExceeded(
            f"AI features aren't available on the {plan['name']} plan. Upgrade to Base or Pro to generate drafts, images and suggestions."
        )
    budget = Decimal(str(plan["ai_budget_usd_per_workspace"]))
    usage = get_or_create_current_usage(workspace)
    if usage.cost_usd >= budget:
        raise UsageLimitExceeded(
            f"{workspace.name} has used its ${budget} AI budget for this month on the {plan['name']} plan. "
            f"It renews next month, or use a different avatar with budget remaining."
        )


@transaction.atomic
def record_ai_cost(workspace, cost_usd):
    """Call after a successful Claude/OpenAI response with its real computed cost."""
    if not cost_usd:
        return
    usage = WorkspaceUsage.objects.select_for_update().get_or_create(
        workspace=workspace, period_start=WorkspaceUsage.current_period_start()
    )[0]
    usage.cost_usd += Decimal(str(cost_usd))
    usage.save(update_fields=["cost_usd"])


def workspace_usage_summary(workspace):
    sub, plan = _plan_for_workspace(workspace)
    usage = get_or_create_current_usage(workspace)
    budget = Decimal(str(plan["ai_budget_usd_per_workspace"]))
    return {
        "workspace_id": workspace.id, "workspace_name": workspace.name,
        "ai_enabled": plan["ai_enabled"],
        "spend_usd": float(usage.cost_usd), "budget_usd": float(budget),
        "pct_used": float(min(Decimal(100), (usage.cost_usd / budget * 100))) if budget else (100.0 if plan["ai_enabled"] is False else 0.0),
    }


def account_usage_summary(user):
    """Everything the Billing page needs: plan, status, per-workspace AI spend, avatar limits."""
    sub = get_or_create_subscription(user)
    plan = PLANS[sub.plan]
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


def check_workspace_limit(user):
    """Call before creating a new workspace. Raises UsageLimitExceeded at the plan's cap."""
    from brand.models import Workspace
    sub = get_or_create_subscription(user)
    plan = PLANS[sub.plan]
    count = Workspace.objects.filter(owner=user).count()
    if count >= plan["max_workspaces"]:
        raise UsageLimitExceeded(
            f"The {plan['name']} plan allows {plan['max_workspaces']} "
            f"{'avatar' if plan['max_workspaces'] == 1 else 'avatars'}. Upgrade to add more."
        )
    # Beyond the plan's included avatars, each additional one has a billing
    # consequence (Pro: +₹100/month), surfaced to the user before they confirm —
    # the actual Stripe line-item update happens after creation succeeds.


def pending_extra_avatar_cost(user):
    """What the NEXT workspace creation would add to the monthly bill, in INR —
    None if it's still within the plan's included count."""
    from brand.models import Workspace
    sub = get_or_create_subscription(user)
    plan = PLANS[sub.plan]
    count = Workspace.objects.filter(owner=user).count()
    if count < plan["included_workspaces"]:
        return None
    return plan["extra_workspace_price_inr"]
