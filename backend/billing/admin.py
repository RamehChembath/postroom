from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from .models import Subscription, WorkspaceUsage, AIUsageEvent, PlanConfig


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ["user_email", "plan", "status", "current_period_end", "cancel_at_period_end", "stripe_customer_id"]
    list_filter = ["plan", "status", "cancel_at_period_end"]
    search_fields = ["user__email", "stripe_customer_id", "stripe_subscription_id"]
    list_editable = ["plan", "status"]  # comp a user, fix a stuck state — no Stripe round-trip needed
    readonly_fields = ["created_at", "updated_at"]
    actions = ["reset_this_months_usage"]

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.action(description="Reset this month's AI spend to $0 (support override)")
    def reset_this_months_usage(self, request, queryset):
        count = 0
        for sub in queryset:
            updated = WorkspaceUsage.objects.filter(
                workspace__owner=sub.user, period_start=WorkspaceUsage.current_period_start()
            ).update(cost_usd=0)
            count += updated
        self.message_user(request, f"Reset AI spend for {count} avatar(s).")


@admin.register(WorkspaceUsage)
class WorkspaceUsageAdmin(ModelAdmin):
    list_display = ["workspace_name", "owner_email", "period_start", "cost_usd", "budget_bar"]
    list_filter = ["period_start"]
    search_fields = ["workspace__name", "workspace__owner__email"]
    ordering = ["-period_start", "-cost_usd"]

    @admin.display(description="Avatar")
    def workspace_name(self, obj):
        return obj.workspace.name

    @admin.display(description="Owner", ordering="workspace__owner__email")
    def owner_email(self, obj):
        return obj.workspace.owner.email

    @admin.display(description="vs. $3 budget")
    def budget_bar(self, obj):
        from .plans import get_plans
        sub = getattr(obj.workspace.owner, "subscription", None)
        budget = get_plans()[sub.plan]["ai_budget_usd_per_workspace"] if sub else 0
        pct = min(100, round(float(obj.cost_usd) / budget * 100)) if budget else 100
        color = "#C0392B" if pct >= 90 else "#C8860D" if pct >= 70 else "#1B7A4A"
        return format_html(
            '<div style="width:120px;background:#eee;border-radius:4px;overflow:hidden">'
            '<div style="width:{}%;background:{};height:14px"></div></div> ${}/${}',
            pct, color, obj.cost_usd, budget,
        )


@admin.register(AIUsageEvent)
class AIUsageEventAdmin(ModelAdmin):
    list_display = ["workspace", "purpose", "model", "cost_usd", "created_at"]
    list_filter = ["purpose", "model"]
    search_fields = ["workspace__name"]
    date_hierarchy = "created_at"


@admin.register(PlanConfig)
class PlanConfigAdmin(ModelAdmin):
    list_display = ["name", "key", "price_monthly_inr", "max_workspaces", "ai_enabled", "ai_budget_usd_per_workspace"]
    list_editable = ["price_monthly_inr", "max_workspaces", "ai_enabled", "ai_budget_usd_per_workspace"]
