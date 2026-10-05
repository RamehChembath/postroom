from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ContentPlanViewSet, PlannedItemViewSet, PostViewSet, DashboardView, PerformanceAnalysisView

router = DefaultRouter()
router.register("plans", ContentPlanViewSet, basename="plan")
router.register("planned-items", PlannedItemViewSet, basename="planned-item")
router.register("posts", PostViewSet, basename="post")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/analyze/", PerformanceAnalysisView.as_view(), name="dashboard-analyze"),
] + router.urls
