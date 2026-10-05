"""
Cloudflare Turnstile verification. Free CAPTCHA alternative — the frontend
renders a widget and gets a token, which we verify server-side here before
letting registration (or any other spam-prone endpoint) through.

If TURNSTILE_SECRET_KEY isn't set, verification is skipped — this is how local
dev and testing work without needing real Cloudflare keys. Set the key in
production and this becomes a hard requirement.
"""
import logging
import urllib.request
import urllib.parse
import json
from django.conf import settings

logger = logging.getLogger(__name__)
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_turnstile(token: str, remote_ip: str = "") -> bool:
    if not settings.TURNSTILE_SECRET_KEY:
        return True  # not configured — don't block local dev/testing
    if not token:
        return False
    data = urllib.parse.urlencode({
        "secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": remote_ip,
    }).encode()
    try:
        with urllib.request.urlopen(VERIFY_URL, data=data, timeout=8) as resp:
            result = json.loads(resp.read())
        return bool(result.get("success"))
    except Exception:
        logger.exception("Turnstile verification request failed")
        return False
