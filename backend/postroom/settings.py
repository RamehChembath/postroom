"""
Django settings for Postroom.
All environment-specific values come from env vars (see .env.example).
"""
import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key, default=None, cast=str):
    val = os.environ.get(key, default)
    if val is None:
        return val
    if cast is bool:
        return str(val).lower() in ("1", "true", "yes", "on")
    if cast is int:
        return int(val)
    return cast(val)


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env("DJANGO_DEBUG", "false", bool)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
COOKIE_DOMAIN = env("COOKIE_DOMAIN", "")  # e.g. ".postroom.in" in prod so api.* and the app share the cookie; blank in dev

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "accounts",
    "brand",
    "content",
    "engagement",
    "notifications",
    "billing",
    "platformconfig",
    "platform_admin",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "postroom.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "postroom.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "postroom"),
        "USER": env("POSTGRES_USER", "postroom"),
        "PASSWORD": env("POSTGRES_PASSWORD", "postroom"),
        "HOST": env("POSTGRES_HOST", "db"),
        "PORT": env("POSTGRES_PORT", "5432"),
    }
}
# Local/dev fallback: if explicitly requested, use SQLite (handy for quick checks without Postgres running).
if env("USE_SQLITE", "false", bool):
    DATABASES["default"] = {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- DRF / JWT ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.cookies.CookieJWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth": "20/hour",       # login/register/password-reset — brute-force protection
        "user": "300/minute",    # general ceiling per logged-in user across the whole API
    },
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# ---- CORS ----
CORS_ALLOWED_ORIGINS = [o.strip() for o in env("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = True  # required: the frontend sends the auth cookie cross-subdomain

# ---- Email (for posting-room reminders) ----
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env("EMAIL_PORT", "587", int)
EMAIL_USE_TLS = env("EMAIL_USE_TLS", "true", bool)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Postroom <noreply@postroom.in>")

# ---- Celery ----
CELERY_BROKER_URL = env("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", "redis://redis:6379/0")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# ---- Cloudflare Turnstile (spam/bot protection on signup) ----
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", "")
# Blank secret key = Turnstile disabled (e.g. local dev) — register works without a token.

# ---- AI providers ----
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-sonnet-5")
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
OPENAI_TEXT_MODEL = env("OPENAI_TEXT_MODEL", "gpt-5")
OPENAI_IMAGE_MODEL = env("OPENAI_IMAGE_MODEL", "gpt-image-1")
# "claude" (recommended) or "openai" — which provider writes post text, tone analysis, strategy and replies.
TEXT_PROVIDER = env("TEXT_PROVIDER", "claude")

FRONTEND_URL = env("FRONTEND_URL", "http://localhost:3000")

# ---- Stripe ----
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_BASE = env("STRIPE_PRICE_BASE", "")
STRIPE_PRICE_PRO = env("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_PRO_EXTRA_AVATAR = env("STRIPE_PRICE_PRO_EXTRA_AVATAR", "")

# ---- Admin theme (django-unfold) ----
UNFOLD = {
    "SITE_TITLE": "Postroom Admin",
    "SITE_HEADER": "Postroom",
    "SITE_SUBHEADER": "Platform administration",
    "SITE_SYMBOL": "forum",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "COLORS": {
        "primary": {
            "50": "239 246 255", "100": "219 234 254", "200": "191 219 254",
            "300": "147 197 253", "400": "96 165 250", "500": "10 102 194",
            "600": "9 92 175", "700": "7 77 146", "800": "6 61 117", "900": "5 49 94",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Platform",
                "items": [
                    {"title": "Users", "icon": "people", "link": "/admin/auth/user/"},
                    {"title": "Avatars (workspaces)", "icon": "badge", "link": "/admin/brand/workspace/"},
                    {"title": "Subscriptions", "icon": "credit_card", "link": "/admin/billing/subscription/"},
                    {"title": "AI usage", "icon": "bolt", "link": "/admin/billing/workspaceusage/"},
                    {"title": "AI provider settings", "icon": "settings", "link": "/admin/platformconfig/aisettings/"},
                ],
            },
            {
                "title": "Content",
                "items": [
                    {"title": "Posts", "icon": "article", "link": "/admin/content/post/"},
                    {"title": "Content plans", "icon": "calendar_month", "link": "/admin/content/contentplan/"},
                    {"title": "Comments", "icon": "chat_bubble", "link": "/admin/engagement/comment/"},
                    {"title": "Goals", "icon": "flag", "link": "/admin/brand/goal/"},
                ],
            },
        ],
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
}
