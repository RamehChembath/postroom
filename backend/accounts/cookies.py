"""
Cookie-based JWT auth: tokens live in httpOnly cookies instead of being
handed to JS, which closes the XSS-can-steal-your-session gap of storing
them in localStorage. The access token is still a normal SimpleJWT token;
this just controls where it's read from and how it's delivered.
"""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

ACCESS_COOKIE = "postroom_access"
REFRESH_COOKIE = "postroom_refresh"

# Subdomains of the same site (api.postroom.in + postroom.in) count as same-site for
# cookie purposes, so Lax is enough and avoids the stricter rules SameSite=None carries.
COOKIE_KWARGS = dict(
    httponly=True,
    secure=not settings.DEBUG,
    samesite="Lax",
    domain=getattr(settings, "COOKIE_DOMAIN", None) or None,
)


def set_auth_cookies(response, access, refresh=None):
    response.set_cookie(ACCESS_COOKIE, access, max_age=60 * 60 * 12, **COOKIE_KWARGS)
    if refresh is not None:
        response.set_cookie(REFRESH_COOKIE, refresh, max_age=60 * 60 * 24 * 14, **COOKIE_KWARGS)
    return response


def clear_auth_cookies(response):
    response.delete_cookie(ACCESS_COOKIE, domain=COOKIE_KWARGS["domain"])
    response.delete_cookie(REFRESH_COOKIE, domain=COOKIE_KWARGS["domain"])
    return response


class CookieJWTAuthentication(JWTAuthentication):
    """Same as SimpleJWT's default, but reads the access token from the
    httpOnly cookie when there's no Authorization header (the API is also
    usable with a bearer token directly, e.g. for scripts/testing)."""

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            raw_token = request.COOKIES.get(ACCESS_COOKIE)
            if raw_token is None:
                return None
        else:
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
