from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PlatformOverviewView, PlanConfigViewSet

router = DefaultRouter()
router.register("plan-configs", PlanConfigViewSet, basename="plan-config")

urlpatterns = [
    path("overview/", PlatformOverviewView.as_view(), name="platform-overview"),
] + router.urls
