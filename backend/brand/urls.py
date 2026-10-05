from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    WorkspaceViewSet, BrandProfileView, AnalyzeWebsiteView, OnboardingPreviewView, AnalyzeToneView, SuggestTopicsView,
    ReferenceImageViewSet, PastPostViewSet, BlockedDateViewSet, GoalViewSet,
)

router = DefaultRouter()
router.register("workspaces", WorkspaceViewSet, basename="workspace")
router.register("reference-images", ReferenceImageViewSet, basename="reference-image")
router.register("past-posts", PastPostViewSet, basename="past-post")
router.register("blocked-dates", BlockedDateViewSet, basename="blocked-date")
router.register("goals", GoalViewSet, basename="goal")

urlpatterns = [
    path("profile/", BrandProfileView.as_view(), name="brand-profile"),
    path("profile/analyze-website/", AnalyzeWebsiteView.as_view(), name="brand-analyze-website"),
    path("profile/preview/", OnboardingPreviewView.as_view(), name="brand-preview"),
    path("profile/analyze-tone/", AnalyzeToneView.as_view(), name="brand-analyze-tone"),
    path("profile/suggest-topics/", SuggestTopicsView.as_view(), name="brand-suggest-topics"),
] + router.urls
