"""Thin wrapper around the stripe SDK — isolated so it's the one place that
touches the network, and so tests can monkeypatch these three functions
instead of the whole stripe module."""
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_or_create_customer(user, subscription):
    if subscription.stripe_customer_id:
        return subscription.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, name=user.first_name or user.email, metadata={"user_id": user.id})
    subscription.stripe_customer_id = customer.id
    subscription.save(update_fields=["stripe_customer_id"])
    return customer.id


def create_checkout_session(customer_id, price_id, success_url, cancel_url):
    return stripe.checkout.Session.create(
        customer=customer_id, mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url, cancel_url=cancel_url,
        allow_promotion_codes=True,
    )


def create_portal_session(customer_id, return_url):
    return stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)


def construct_webhook_event(payload, sig_header):
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)


def create_subscription_item(subscription_id, price_id, quantity):
    return stripe.SubscriptionItem.create(subscription=subscription_id, price=price_id, quantity=quantity)


def modify_subscription_item_quantity(item_id, quantity):
    return stripe.SubscriptionItem.modify(item_id, quantity=quantity)


def delete_subscription_item(item_id):
    return stripe.SubscriptionItem.delete(item_id)
