from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin
from .models import AISettings


@admin.register(AISettings)
class AISettingsAdmin(ModelAdmin):
    """Singleton settings page: always edits the one row, never shows an 'add
    another' option, never allows deleting it."""
    fields = ["anthropic_api_key", "openai_api_key", "updated_at"]
    readonly_fields = ["updated_at"]

    def has_add_permission(self, request):
        return not AISettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Skip the list page entirely — go straight to the (only) settings form.
        obj = AISettings.load()
        return redirect(reverse("admin:platformconfig_aisettings_change", args=[obj.pk]))
