import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import AccountProfile
from .tokens import email_verification_token

logger = logging.getLogger(__name__)


def send_verification_email(user):
    profile, _ = AccountProfile.objects.get_or_create(user=user)
    if profile.email_verified:
        return False
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    link = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
    try:
        send_mail(
            "Confirm your Postroom email",
            render_to_string("accounts/verify_email.txt", {"user": user, "link": link}),
            settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send verification email to %s", user.email)
        return False
    profile.verification_sent_at = timezone.now()
    profile.save(update_fields=["verification_sent_at"])
    return True
