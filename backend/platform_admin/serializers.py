from rest_framework import serializers
from billing.models import PlanConfig, Feature, PlanFeature


class FeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feature
        fields = ["id", "key", "name", "description", "category", "value_kind", "unit", "tier_options", "order"]


class PlanFeatureSerializer(serializers.ModelSerializer):
    feature = FeatureSerializer(read_only=True)
    feature_id = serializers.PrimaryKeyRelatedField(queryset=Feature.objects.all(), source="feature", write_only=True)

    class Meta:
        model = PlanFeature
        fields = ["id", "feature", "feature_id", "enabled", "quantity", "tier"]


class PlanConfigSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()
    subscriber_count = serializers.SerializerMethodField()

    class Meta:
        model = PlanConfig
        fields = [
            "id", "key", "name", "order", "price_monthly_inr",
            "included_workspaces", "max_workspaces", "extra_workspace_price_inr",
            "ai_budget_usd_per_workspace", "is_default_free",
            "stripe_price_id", "stripe_extra_avatar_price_id", "updated_at",
            "features", "subscriber_count",
        ]
        read_only_fields = ["key", "updated_at"]  # key is auto-slugged from name on create, fixed after that

    def get_features(self, plan):
        from billing.plans import _ensure_seeded
        _ensure_seeded()
        # Ensure every catalog feature has a row for this plan (lazily, so adding
        # a new feature to the catalog doesn't require touching every plan).
        existing = {pf.feature_id for pf in plan.plan_features.all()}
        for feature in Feature.objects.all():
            if feature.id not in existing:
                PlanFeature.objects.get_or_create(plan=plan, feature=feature)
        return PlanFeatureSerializer(plan.plan_features.select_related("feature").order_by("feature__order"), many=True).data

    def get_subscriber_count(self, plan):
        from billing.models import Subscription
        return Subscription.objects.filter(plan=plan.key, status="active").count()
