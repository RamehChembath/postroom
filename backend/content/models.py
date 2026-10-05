from django.conf import settings
from django.db import models
from brand.models import Workspace


class ContentPlan(models.Model):
    """The brief submitted in Strategy: subject, how much to write, over what window."""
    STATUS_CHOICES = [
        ("draft", "Draft"),            # brief submitted, calendar not yet generated
        ("proposed", "Proposed"),      # calendar of titles+dates generated, awaiting approval
        ("approved", "Approved"),      # titles approved, full drafts being/been generated
    ]
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="content_plans")
    subject = models.CharField(max_length=300)
    brief = models.TextField(blank=True)
    num_posts = models.PositiveSmallIntegerField(default=4)
    num_articles = models.PositiveSmallIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PlannedItem(models.Model):
    """One proposed title+date in a plan's calendar, approved/edited before a full draft is written."""
    TYPE_CHOICES = [("post", "Post"), ("article", "Article")]
    STATUS_CHOICES = [("suggested", "Suggested"), ("approved", "Approved"), ("rejected", "Rejected")]

    plan = models.ForeignKey(ContentPlan, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=300)
    angle = models.TextField(blank=True, help_text="The hook/angle Claude proposed for this title.")
    item_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="post")
    suggested_date = models.DateField()
    date_rationale = models.CharField(max_length=300, blank=True, help_text="Why this date — e.g. \"Tuesday, high-engagement day\".")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="suggested")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "suggested_date"]


class Post(models.Model):
    """A full post or article — AI-drafted from a PlannedItem, or written/pasted directly."""
    TYPE_CHOICES = [("post", "Post"), ("article", "Article")]
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending_approval", "Pending your approval"),
        ("approved", "Approved"),        # sits in the Posting Room
        ("posted", "Posted"),
    ]

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="posts")
    plan = models.ForeignKey(ContentPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    planned_item = models.OneToOneField(PlannedItem, on_delete=models.SET_NULL, null=True, blank=True, related_name="post")

    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="post")
    title = models.CharField(max_length=300, blank=True)
    text = models.TextField(blank=True)
    hashtags = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    scheduled_at = models.DateTimeField(null=True, blank=True)
    posted_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    # Logged manually after posting (LinkedIn's API doesn't expose this to personal apps).
    likes = models.PositiveIntegerField(default=0)
    reach = models.PositiveIntegerField(default=0, help_text="Impressions, self-reported from LinkedIn's post analytics.")

    predicted_score = models.PositiveSmallIntegerField(null=True, blank=True)
    predicted_reason = models.TextField(blank=True)
    predicted_tip = models.TextField(blank=True)

    next_step_suggestion = models.TextField(blank=True)
    next_step_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def final_text(self):
        return f"{self.text}\n\n{self.hashtags}".strip() if self.hashtags else self.text


class PostImage(models.Model):
    SOURCE_CHOICES = [("generated", "AI generated"), ("uploaded", "Uploaded")]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="post_images/")
    prompt = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="generated")
    created_at = models.DateTimeField(auto_now_add=True)
