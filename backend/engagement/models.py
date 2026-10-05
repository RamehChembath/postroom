from django.db import models
from content.models import Post


class Comment(models.Model):
    """A comment logged manually against one of the user's posts, with an AI-suggested reply."""
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    person_name = models.CharField(max_length=200, blank=True)
    person_title = models.CharField(max_length=200, blank=True, help_text="Role/company, if known — improves reply quality.")
    text = models.TextField()
    reply = models.TextField(blank=True)
    reply_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
