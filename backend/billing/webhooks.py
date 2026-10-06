"""Stripe webhook event handling, separated from the HTTP view so it can be
tested by calling handle_event() directly with a constructed event dict —
no real Stripe signature or network call needed for that."""
import logging
from datetime import timezone as dt_timezone
from django.utils import timezone
from .models import Subscription
from .plans import plan_for_price_id, default_free_plan_key

logger = logging.getLogger(__name__)

STRIPE_STATUS_MAP = {
    "trialing": "trialing", "active": "active",
    "past_due": "past_due", "unpaid": "past_due", "incomplete": "past_due",
    "canceled": "canceled", "incomplete_expired": "canceled",
}


def _apply_stripe_subscription(sub: Subscription, stripe_sub: dict):
    # A Pro subscription can carry TWO line items (the base Pro price + the
    # extra-avatar add-on) — find whichever item is a known PLAN price, not
    # just the first item, since Stripe doesn't guarantee item order.
    items = stripe_sub.get("items", {}).get("data", [])
    plan_key = None
    for item in items:
        plan_key = plan_for_price_id(item["price"]["id"])
        if plan_key:
            break
    if plan_key:
        sub.plan = plan_key
    sub.status = STRIPE_STATUS_MAP.get(stripe_sub.get("status"), sub.status)
    sub.stripe_subscription_id = stripe_sub["id"]
    period_end = stripe_sub.get("current_period_end")
    if period_end:
        sub.current_period_end = timezone.datetime.fromtimestamp(period_end, tz=dt_timezone.utc)
    sub.cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end"))
    sub.save()


def handle_event(event: dict):
    etype = event.get("type")
    data = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        customer_id = data.get("customer")
        stripe_sub = data.get("subscription")
        sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if not sub:
            logger.warning("checkout.session.completed for unknown customer %s", customer_id)
            return
        # The session gives us the subscription id; the full object (with price/status) comes
        # via the customer.subscription.* events that Stripe fires alongside this one — if the
        # session itself already carries expanded data, apply it directly.
        if isinstance(stripe_sub, dict):
            _apply_stripe_subscription(sub, stripe_sub)

    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        customer_id = data.get("customer")
        sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if sub:
            _apply_stripe_subscription(sub, data)
        else:
            logger.warning("%s for unknown customer %s", etype, customer_id)

    elif etype == "customer.subscription.deleted":
        customer_id = data.get("customer")
        sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if sub:
            sub.plan = default_free_plan_key()
            sub.status = "active"
            sub.stripe_subscription_id = ""
            sub.cancel_at_period_end = False
            sub.save()

    elif etype == "invoice.payment_failed":
        customer_id = data.get("customer")
        sub = Subscription.objects.filter(stripe_customer_id=customer_id).first()
        if sub:
            sub.status = "past_due"
            sub.save(update_fields=["status"])

    else:
        logger.info("Unhandled Stripe event type: %s", etype)
