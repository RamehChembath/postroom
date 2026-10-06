from rest_framework import serializers
from billing.models import PlanConfig


class PlanConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanConfig
        fields = [
            "id", "key", "name", "order", "price_monthly_inr",
            "included_workspaces", "max_workspaces", "extra_workspace_price_inr",
            "ai_enabled", "ai_budget_usd_per_workspace",
            "stripe_price_id", "stripe_extra_avatar_price_id", "updated_at",
        ]
        read_only_fields = ["key", "updated_at"]  # the plan's identity (free/base/pro) isn't editable, everything it provides is
