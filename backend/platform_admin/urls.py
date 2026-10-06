from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PlatformOverviewView, PlanConfigViewSet, FeatureCatalogViewSet

router = DefaultRouter()
router.register("plan-configs", PlanConfigViewSet, basename="plan-config")
router.register("features", FeatureCatalogViewSet, basename="feature-catalog")

urlpatterns = [
    path("overview/", PlatformOverviewView.as_view(), name="platform-overview"),
] + router.urls
