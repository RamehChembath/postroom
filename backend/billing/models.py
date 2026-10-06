from django.conf import settings
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"), ("trialing", "Trialing"),
        ("past_due", "Past due"), ("canceled", "Canceled"),
    ]
    PLAN_CHOICES = [("free", "Free"), ("base", "Base"), ("pro", "Pro")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription")
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default="free")
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
    """What each plan actually provides — editable from Settings → Plan Builder
    instead of a code change + deploy. Seeded once from billing/plans.py's
    defaults; after that, this table is the source of truth."""
    PLAN_CHOICES = [("free", "Free"), ("base", "Base"), ("pro", "Pro")]

    key = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    name = models.CharField(max_length=50)
    order = models.PositiveSmallIntegerField(default=0)
    price_monthly_inr = models.PositiveIntegerField(default=0)
    included_workspaces = models.PositiveSmallIntegerField(default=1)
    max_workspaces = models.PositiveSmallIntegerField(default=1)
    extra_workspace_price_inr = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = no additional avatars allowed on this plan.")
    ai_enabled = models.BooleanField(default=True)
    ai_budget_usd_per_workspace = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    stripe_extra_avatar_price_id = models.CharField(max_length=100, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


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
