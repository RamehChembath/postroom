from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/brand/", include("brand.urls")),
    path("api/content/", include("content.urls")),
    path("api/engagement/", include("engagement.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/platform/", include("platform_admin.urls")),
    path("api/platform/", include("platformconfig.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
