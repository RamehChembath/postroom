import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .plans import PLANS
from .usage import get_or_create_subscription, account_usage_summary, pending_extra_avatar_cost
from . import stripe_client, webhooks

logger = logging.getLogger(__name__)


class PlansView(APIView):
    """Public pricing info — no Stripe price ids exposed, just what the user picks from."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({k: {kk: vv for kk, vv in v.items() if kk != "stripe_price_id"} for k, v in PLANS.items()})


class UsageSummaryView(APIView):
    def get(self, request):
        data = account_usage_summary(request.user)
        data["pending_extra_avatar_cost_inr"] = pending_extra_avatar_cost(request.user)
        return Response(data)


class CreateCheckoutSessionView(APIView):
    def post(self, request):
        plan_key = request.data.get("plan")
        if plan_key not in ("base", "pro"):
            return Response({"detail": "plan must be 'base' or 'pro'."}, status=status.HTTP_400_BAD_REQUEST)
        price_id = PLANS[plan_key]["stripe_price_id"]
        if not price_id:
            return Response({"detail": "Billing isn't configured on this server yet."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        sub = get_or_create_subscription(request.user)
        try:
            customer_id = stripe_client.get_or_create_customer(request.user, sub)
            session = stripe_client.create_checkout_session(
                customer_id, price_id,
                success_url=f"{settings.FRONTEND_URL}/billing?checkout=success",
                cancel_url=f"{settings.FRONTEND_URL}/billing?checkout=canceled",
            )
        except Exception as e:
            logger.exception("Stripe checkout session creation failed")
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"url": session.url})


class CreatePortalSessionView(APIView):
    def post(self, request):
        sub = get_or_create_subscription(request.user)
        if not sub.stripe_customer_id:
            return Response({"detail": "No billing account yet — subscribe to a paid plan first."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = stripe_client.create_portal_session(sub.stripe_customer_id, return_url=f"{settings.FRONTEND_URL}/billing")
        except Exception as e:
            logger.exception("Stripe portal session creation failed")
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"url": session.url})


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """Stripe calls this directly — no user auth, verified by signature instead."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe_client.construct_webhook_event(request.body, sig_header)
        except Exception as e:
            logger.warning("Stripe webhook signature verification failed: %s", e)
            return Response({"detail": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            webhooks.handle_event(event)
        except Exception:
            logger.exception("Error handling Stripe webhook event %s", event.get("type"))
            return Response({"detail": "Webhook handler error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"received": True})
