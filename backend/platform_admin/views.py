"""
Staff-only platform operations API: real cost/margin/tenant data, computed
from AIUsageEvent (per-call cost+purpose+model) and Subscription records —
nothing here is fabricated; it's all aggregated from what the app actually logs.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework import viewsets

from billing.models import AIUsageEvent, Subscription, PlanConfig
from billing.plans import get_plans, _ensure_seeded
from .serializers import PlanConfigSerializer

# Illustrative USD->INR rate for the margin estimate shown on this dashboard —
# update to your real rate, or wire in a live FX source, before trusting the
# margin number for real decisions.
USD_TO_INR = Decimal("83")

RANGE_DAYS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}


class PlatformOverviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = RANGE_DAYS.get(request.query_params.get("range", "30d"), 30)
        since = timezone.now() - timedelta(days=days)
        events = AIUsageEvent.objects.filter(created_at__gte=since)

        total_cost = events.aggregate(s=Sum("cost_usd"))["s"] or Decimal(0)
        total_calls = events.count()

        daily = (events.annotate(day=TruncDate("created_at")).values("day")
                  .annotate(cost=Sum("cost_usd"), calls=Count("id")).order_by("day"))

        by_purpose = (events.values("purpose").annotate(cost=Sum("cost_usd"), calls=Count("id"))
                      .order_by("-cost"))
        by_model = (events.exclude(model="").values("model").annotate(cost=Sum("cost_usd"), calls=Count("id"))
                    .order_by("-cost"))

        top_calls = events.order_by("-cost_usd")[:10].values(
            "workspace__name", "purpose", "model", "cost_usd", "created_at"
        )

        # Per-user ("tenant") breakdown: plan, cost across all their workspaces in
        # range, and an estimated margin against their current plan price. The
        # "fees billed" figure is a snapshot of their current plan price, not a
        # real invoice total — call it what it is on the frontend.
        tenants = []
        total_fees = Decimal(0)
        for user in User.objects.filter(is_staff=False).select_related("subscription"):
            sub = getattr(user, "subscription", None)
            plan_key = sub.plan if sub else "free"
            plan = get_plans()[plan_key]
            ws_ids = list(user.workspaces.values_list("id", flat=True))
            user_cost = events.filter(workspace_id__in=ws_ids).aggregate(s=Sum("cost_usd"))["s"] or Decimal(0)
            fees = Decimal(plan["price_monthly_inr"]) if (sub and sub.status == "active" and plan_key != "free") else Decimal(0)
            total_fees += fees
            margin = fees - (user_cost * USD_TO_INR)
            tenants.append({
                "user_id": user.id, "name": user.first_name or user.email, "email": user.email,
                "status": sub.status if sub else "free", "plan": plan["name"],
                "workspace_count": len(ws_ids),
                "cost_usd": float(user_cost), "fees_inr": float(fees), "margin_inr": round(float(margin), 2),
            })
        tenants.sort(key=lambda t: t["cost_usd"], reverse=True)

        estimated_margin = total_fees - (total_cost * USD_TO_INR)

        return Response({
            "range": request.query_params.get("range", "30d"),
            "total_cost_usd": float(total_cost),
            "total_calls": total_calls,
            "subscription_fees_inr": float(total_fees),
            "estimated_margin_inr": round(float(estimated_margin), 2),
            "fx_note": f"Margin assumes 1 USD = ₹{USD_TO_INR} — update USD_TO_INR in platform_admin/views.py to your real rate.",
            "daily": [{"date": d["day"].isoformat(), "cost_usd": float(d["cost"] or 0), "calls": d["calls"]} for d in daily],
            "by_purpose": [{"purpose": p["purpose"], "calls": p["calls"], "cost_usd": float(p["cost"] or 0)} for p in by_purpose],
            "by_model": [{"model": m["model"], "calls": m["calls"], "cost_usd": float(m["cost"] or 0)} for m in by_model],
            "tenants": tenants,
            "top_expensive_calls": [
                {"workspace": c["workspace__name"], "purpose": c["purpose"], "model": c["model"],
                 "cost_usd": float(c["cost_usd"]), "created_at": c["created_at"]}
                for c in top_calls
            ],
        })


class PlanConfigViewSet(viewsets.ModelViewSet):
    """Plan Builder: list and edit what each plan (Free/Base/Pro) actually
    provides. Plans aren't created/deleted here — the three tiers are fixed
    by `key` (used throughout billing logic) — only their limits/pricing are
    editable. Takes effect immediately; no deploy needed."""
    permission_classes = [IsAdminUser]
    serializer_class = PlanConfigSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        _ensure_seeded()
        return PlanConfig.objects.all()
