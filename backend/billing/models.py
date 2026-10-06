from django.conf import settings
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"), ("trialing", "Trialing"),
        ("past_due", "Past due"), ("canceled", "Canceled"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    # Free-text, matching whatever PlanConfig.key this user is on — plans are
    # fully dynamic now (admin can create/delete as many as they want), so
    # this can't be a fixed choices field anymore.
    plan = models.CharField(max_length=40, default="free")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    # The Stripe subscription-item id for the "extra avatar" line item (Pro only,
    # only present once a 2nd+ avatar has been added) — tracked so we can update
    # or remove its quantity without having to search Stripe for it each time.
    stripe_extra_avatar_item_id = models.CharField(max_length=100, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.plan} ({self.status})"


class AIUsageEvent(models.Model):
    """One row per Claude/OpenAI call — what it was for, which model, what it
    actually cost. This is what powers the real cost-by-purpose / cost-by-model
    / most-expensive-calls breakdowns, not just a monthly total."""
    workspace = models.ForeignKey("brand.Workspace", on_delete=models.CASCADE, related_name="ai_usage_events")
    purpose = models.CharField(max_length=40)   # e.g. "draft", "tone_analysis", "image", "reply"
    model = models.CharField(max_length=80, blank=True)
    cost_usd = models.DecimalField(max_digits=8, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["purpose"]), models.Index(fields=["model"])]


class PlanConfig(models.Model):
    """What a plan provides — editable (and now creatable/deletable) from
    Settings → Plan Builder, no code change or deploy needed. Plans are fully
    dynamic: `key` is just a unique slug, not a fixed set of choices."""
    key = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=0)
    price_monthly_inr = models.PositiveIntegerField(default=0)
    included_workspaces = models.PositiveSmallIntegerField(default=1)
    max_workspaces = models.PositiveSmallIntegerField(default=1)
    extra_workspace_price_inr = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = no additional avatars allowed on this plan.")
    ai_budget_usd_per_workspace = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Safety cap on AI $ spend per avatar/month, on top of the per-feature quotas below.")
    stripe_price_id = models.CharField(max_length=100, blank=True)
    stripe_extra_avatar_price_id = models.CharField(max_length=100, blank=True)
    is_default_free = models.BooleanField(default=False, help_text="Canceled/downgraded subscriptions fall back to whichever plan has this set. Exactly one plan should have it.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.key:
            from django.utils.text import slugify
            base = slugify(self.name)[:36] or "plan"
            key = base
            n = 2
            while PlanConfig.objects.filter(key=key).exclude(pk=self.pk).exists():
                key = f"{base}-{n}"[:40]
                n += 1
            self.key = key
        super().save(*args, **kwargs)
        if self.is_default_free:
            PlanConfig.objects.exclude(pk=self.pk).update(is_default_free=False)

    def __str__(self):
        return self.name


class Feature(models.Model):
    """The catalog of things a plan can grant — one row per capability, shared
    across all plans. Each plan then has a PlanFeature row saying whether/how
    much of it that plan includes."""
    CATEGORY_CHOICES = [("ai", "AI-powered"), ("non_ai", "Non-AI")]
    VALUE_KIND_CHOICES = [("boolean", "On / off"), ("quantity", "Quantity per month"), ("tier", "Quality tier")]

    key = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default="ai")
    value_kind = models.CharField(max_length=10, choices=VALUE_KIND_CHOICES, default="boolean")
    unit = models.CharField(max_length=40, blank=True, help_text="e.g. 'posts/month', 'replies/month' — shown next to the quantity.")
    tier_options = models.JSONField(default=list, blank=True, help_text="For 'tier' kind: the allowed values, e.g. [\"none\",\"1_month\",\"3_months\"].")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class PlanFeature(models.Model):
    """One plan's configuration of one feature. Created lazily (get_or_create)
    as plans/features are added, so every plan×feature combination doesn't
    need a migration — just a row."""
    plan = models.ForeignKey(PlanConfig, on_delete=models.CASCADE, related_name="plan_features")
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name="plan_features")
    enabled = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Used when the feature's value kind is 'quantity'.")
    tier = models.CharField(max_length=40, blank=True, help_text="Used when the feature's value kind is 'tier'.")

    class Meta:
        unique_together = ("plan", "feature")


class WorkspaceUsage(models.Model):
    """One row per workspace per calendar month: real USD cost of every Claude/
    OpenAI call made for that avatar, computed from actual token usage each
    provider reports back — not a flat per-action guess."""
    workspace = models.ForeignKey("brand.Workspace", on_delete=models.CASCADE, related_name="usage_records")
    period_start = models.DateField()
    cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    class Meta:
        unique_together = ("workspace", "period_start")

    @staticmethod
    def current_period_start():
        return timezone.localdate().replace(day=1)
