from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Comment


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ["person_name", "post", "has_reply", "created_at"]
    search_fields = ["person_name", "text", "post__title"]
    readonly_fields = ["reply_generated_at", "created_at"]

    @admin.display(description="Replied", boolean=True)
    def has_reply(self, obj):
        return bool(obj.reply)
