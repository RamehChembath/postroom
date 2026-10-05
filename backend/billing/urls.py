from django.urls import path
from .views import PlansView, UsageSummaryView, CreateCheckoutSessionView, CreatePortalSessionView, StripeWebhookView

urlpatterns = [
    path("plans/", PlansView.as_view(), name="billing-plans"),
    path("usage/", UsageSummaryView.as_view(), name="billing-usage"),
    path("checkout/", CreateCheckoutSessionView.as_view(), name="billing-checkout"),
    path("portal/", CreatePortalSessionView.as_view(), name="billing-portal"),
    path("webhook/", StripeWebhookView.as_view(), name="billing-webhook"),
]
