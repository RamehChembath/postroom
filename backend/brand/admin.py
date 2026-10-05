from django.contrib import admin
from .models import Workspace, BrandProfile, ReferenceImage, PastPost, BlockedDate, Goal


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
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
class BrandProfileAdmin(admin.ModelAdmin):
    list_display = ["workspace", "industry", "tone_posts_analyzed", "onboarding_completed"]
    search_fields = ["workspace__name", "workspace__owner__email", "industry"]
    list_filter = ["onboarding_completed"]


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ["title", "workspace", "metric", "target_value", "is_active", "end_date"]
    list_filter = ["metric", "is_active"]
    search_fields = ["title", "workspace__name"]


admin.site.register(ReferenceImage)
admin.site.register(PastPost)
admin.site.register(BlockedDate)
