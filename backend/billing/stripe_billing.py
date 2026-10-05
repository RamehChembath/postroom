"""
Higher-level billing logic that sits on top of stripe_client's raw SDK calls:
keeping a Pro subscription's "extra avatar" line item in sync with how many
workspaces the user actually has.
"""
import logging
from .plans import PLANS
from . import stripe_client

logger = logging.getLogger(__name__)


def sync_extra_avatar_quantity(subscription, workspace_count):
    """Updates (or creates/removes) the extra-avatar Stripe line item so billing
    matches reality. Silently does nothing if the plan has no such add-on, or
    the user isn't on a real Stripe subscription yet (e.g. still on Free) —
    never blocks the workspace create/delete flow on a billing hiccup."""
    plan = PLANS[subscription.plan]
    price_id = plan.get("stripe_extra_avatar_price_id")
    if not price_id or not subscription.stripe_subscription_id:
        return

    extra = max(0, workspace_count - plan["included_workspaces"])
    try:
        if extra == 0:
            if subscription.stripe_extra_avatar_item_id:
                stripe_client.delete_subscription_item(subscription.stripe_extra_avatar_item_id)
                subscription.stripe_extra_avatar_item_id = ""
                subscription.save(update_fields=["stripe_extra_avatar_item_id"])
        elif subscription.stripe_extra_avatar_item_id:
            stripe_client.modify_subscription_item_quantity(subscription.stripe_extra_avatar_item_id, extra)
        else:
            item = stripe_client.create_subscription_item(subscription.stripe_subscription_id, price_id, extra)
            subscription.stripe_extra_avatar_item_id = item.id
            subscription.save(update_fields=["stripe_extra_avatar_item_id"])
    except Exception:
        logger.exception("Failed to sync extra-avatar quantity for subscription %s", subscription.id)
