from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_post_reminder(post):
    subject = f"Postroom: your post is due today — {post.title or post.text[:50]}"
    link = f"{settings.FRONTEND_URL}/posting-room/{post.id}"
    body = render_to_string("notifications/post_reminder.txt", {"post": post, "link": link})
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [post.workspace.owner.email], fail_silently=False)
