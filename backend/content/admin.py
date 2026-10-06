from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import ContentPlan, PlannedItem, Post, PostImage


class PlannedItemInline(TabularInline):
    model = PlannedItem
    extra = 0
    fields = ["title", "item_type", "suggested_date", "status"]


@admin.register(ContentPlan)
class ContentPlanAdmin(ModelAdmin):
    list_display = ["subject", "workspace", "status", "num_posts", "num_articles", "start_date", "end_date"]
    list_filter = ["status"]
    search_fields = ["subject", "workspace__name"]
    inlines = [PlannedItemInline]


@admin.register(PlannedItem)
class PlannedItemAdmin(ModelAdmin):
    list_display = ["title", "plan", "item_type", "suggested_date", "status"]
    list_filter = ["item_type", "status"]
    search_fields = ["title", "plan__subject"]


class PostImageInline(TabularInline):
    model = PostImage
    extra = 0
    readonly_fields = ["source", "created_at"]


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ["title_or_text", "workspace", "type", "status", "likes", "scheduled_at", "posted_at"]
    list_filter = ["status", "type"]
    search_fields = ["title", "text", "workspace__name"]
    inlines = [PostImageInline]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Post")
    def title_or_text(self, obj):
        return obj.title or obj.text[:60]


@admin.register(PostImage)
class PostImageAdmin(ModelAdmin):
    list_display = ["post", "source", "created_at"]
    list_filter = ["source"]
