import logging
from celery import shared_task
from django.utils import timezone
from content.models import Post
from .emails import send_post_reminder

logger = logging.getLogger(__name__)


@shared_task
def send_due_post_reminders():
    """Runs daily (see postroom/celery.py beat schedule). Emails the user for every
    approved post scheduled for today that hasn't had a reminder sent yet."""
    today = timezone.localdate()
    posts = Post.objects.filter(status="approved", scheduled_at__date=today, reminder_sent_at__isnull=True)
    sent = 0
    for post in posts:
        try:
            send_post_reminder(post)
            post.reminder_sent_at = timezone.now()
            post.save(update_fields=["reminder_sent_at"])
            sent += 1
        except Exception:
            logger.exception("Failed to send reminder for post %s", post.id)
    return f"Sent {sent} reminder(s)"
