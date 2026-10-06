from django.db import models


class AISettings(models.Model):
    """A singleton row holding keys/settings an admin can change from the
    Django admin UI instead of editing backend/.env and redeploying.
    These take priority over the equivalent .env values when set (see
    aiengine.providers.get_anthropic_key / get_openai_key) — leave a field
    blank here to fall back to whatever is in .env."""
    anthropic_api_key = models.CharField(max_length=200, blank=True, help_text="Overrides ANTHROPIC_API_KEY in .env when set. Leave blank to use the .env value.")
    openai_api_key = models.CharField(max_length=200, blank=True, help_text="Overrides OPENAI_API_KEY in .env when set. Leave blank to use the .env value.")
    default_claude_model = models.CharField(max_length=80, blank=True, help_text="Overrides CLAUDE_MODEL in .env when set.")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI provider settings"
        verbose_name_plural = "AI provider settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce a single row
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # never allow deleting the singleton

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "AI provider settings"
