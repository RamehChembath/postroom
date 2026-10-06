from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Workspace, BrandProfile, ReferenceImage, PastPost, BlockedDate, Goal


@admin.register(Workspace)
class WorkspaceAdmin(ModelAdmin):
    list_display = ["name", "owner_email", "persona_type", "is_default", "post_count", "created_at"]
    list_filter = ["persona_type", "is_default"]
    search_fields = ["name", "owner__email"]
    readonly_fields = ["created_at"]

    @admin.display(description="Owner", ordering="owner__email")
    def owner_email(self, obj):
        return obj.owner.email

    @admin.display(description="Posts")
    def post_count(self, obj):
        return obj.posts.count()


@admin.register(BrandProfile)
class BrandProfileAdmin(ModelAdmin):
    list_display = ["workspace", "industry", "tone_posts_analyzed", "onboarding_completed"]
    search_fields = ["workspace__name", "workspace__owner__email", "industry"]
    list_filter = ["onboarding_completed"]


@admin.register(Goal)
class GoalAdmin(ModelAdmin):
    list_display = ["title", "workspace", "metric", "target_value", "is_active", "end_date"]
    list_filter = ["metric", "is_active"]
    search_fields = ["title", "workspace__name"]


@admin.register(ReferenceImage)
class ReferenceImageAdmin(ModelAdmin):
    list_display = ["workspace", "note", "created_at"]


@admin.register(PastPost)
class PastPostAdmin(ModelAdmin):
    list_display = ["workspace", "likes", "posted_on", "created_at"]
    search_fields = ["workspace__name"]


@admin.register(BlockedDate)
class BlockedDateAdmin(ModelAdmin):
    list_display = ["workspace", "date", "reason"]
