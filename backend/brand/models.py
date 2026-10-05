from django.conf import settings
from django.db import models


class Workspace(models.Model):
    """One LinkedIn 'avatar' a user manages: themselves, or a company page they post as.
    Each workspace has its own full Strategy / Plan / Posts / Dashboard / Goals — completely separate."""
    PERSONA_CHOICES = [("individual", "Myself"), ("company", "Company spokesperson")]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workspaces")
    name = models.CharField(max_length=150, help_text="e.g. 'Alex (founder)' or 'Northwind — company page'")
    persona_type = models.CharField(max_length=20, choices=PERSONA_CHOICES, default="individual")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_persona_type_display()})"


class BrandProfile(models.Model):
    """One per workspace: who they are, who they write for, and their learned voice."""
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name="brand_profile")

    company_name = models.CharField(max_length=200, blank=True)
    company_website = models.URLField(blank=True)
    website_summary = models.TextField(blank=True, help_text="Claude's summary of the company site, used as writing context.")

    industry = models.CharField(max_length=200, blank=True)
    target_audience = models.TextField(blank=True)
    core_topics = models.CharField(max_length=500, blank=True, help_text="Comma-separated topics.")
    voice_notes = models.TextField(blank=True, help_text="Manual notes: words to avoid, things never to post about, etc.")

    # Learned from the user's own posted content.
    tone_summary = models.TextField(blank=True)
    tone_traits = models.JSONField(default=list, blank=True)
    tone_language = models.TextField(blank=True)
    tone_sample_post = models.TextField(blank=True, help_text="A short sample Claude wrote in this tone, shown with a disclaimer.")
    tone_analyzed_at = models.DateTimeField(null=True, blank=True)
    tone_posts_analyzed = models.PositiveIntegerField(default=0)

    onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BrandProfile<{self.user}>"


class ReferenceImage(models.Model):
    """Images uploaded as a style reference for AI-generated post images, per workspace."""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="reference_images")
    image = models.ImageField(upload_to="reference_images/")
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PastPost(models.Model):
    """Posts pasted in during onboarding for this workspace — used only for tone analysis."""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="past_posts")
    text = models.TextField()
    likes = models.PositiveIntegerField(default=0)
    posted_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BlockedDate(models.Model):
    """Dates to skip when the strategy engine proposes a posting calendar — holidays, leave, etc. Per workspace."""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="blocked_dates")
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ("workspace", "date")
        ordering = ["date"]


class Goal(models.Model):
    METRIC_CHOICES = [("likes", "Likes"), ("comments", "Comments"), ("posts", "Posts published")]
    PERIOD_CHOICES = [("week", "This week"), ("month", "This month"), ("quarter", "This quarter"), ("custom", "Custom range")]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="goals")
    title = models.CharField(max_length=200)
    metric = models.CharField(max_length=20, choices=METRIC_CHOICES, default="likes")
    target_value = models.PositiveIntegerField()
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, default="month")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
