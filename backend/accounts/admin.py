from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from unfold.admin import ModelAdmin, StackedInline
from billing.models import Subscription
from .models import AccountProfile


class AccountProfileInline(StackedInline):
    model = AccountProfile
    can_delete = False
    readonly_fields = ["created_at", "verification_sent_at"]


class SubscriptionInline(StackedInline):
    model = Subscription
    can_delete = False
    readonly_fields = ["stripe_customer_id", "stripe_subscription_id", "created_at", "updated_at"]
    fields = ["plan", "status", "current_period_end", "cancel_at_period_end", "stripe_customer_id", "stripe_subscription_id"]


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(ModelAdmin, DjangoUserAdmin):
    inlines = [AccountProfileInline, SubscriptionInline]
    list_display = ["email", "first_name", "is_verified", "plan_name", "workspace_count", "date_joined", "is_active"]
    list_filter = ["is_active", "is_staff", "date_joined"]
    search_fields = ["email", "first_name", "username"]

    @admin.display(description="Verified", boolean=True)
    def is_verified(self, obj):
        profile = getattr(obj, "account_profile", None)
        return bool(profile and profile.email_verified)

    @admin.display(description="Plan")
    def plan_name(self, obj):
        sub = getattr(obj, "subscription", None)
        return sub.get_plan_display() if sub else "—"

    @admin.display(description="Avatars")
    def workspace_count(self, obj):
        return obj.workspaces.count()


@admin.register(AccountProfile)
class AccountProfileAdmin(ModelAdmin):
    list_display = ["user", "email_verified", "created_at"]
    list_filter = ["email_verified"]
