from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from aiengine import services
from aiengine.providers import AIError, error_response
from billing.usage import UsageLimitExceeded
from .models import Workspace, BrandProfile, ReferenceImage, PastPost, BlockedDate, Goal
from .utils import get_workspace
from .serializers import (
    WorkspaceSerializer, BrandProfileSerializer, ReferenceImageSerializer, PastPostSerializer,
    BlockedDateSerializer, GoalSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    """The user's LinkedIn 'avatars' — themselves, a company page, etc. Listing/creating
    these needs no workspace scoping, since a workspace's owner *is* the scope."""
    serializer_class = WorkspaceSerializer

    def get_queryset(self):
        return Workspace.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        from billing.usage import check_workspace_limit, get_or_create_subscription
        from billing.stripe_billing import sync_extra_avatar_quantity

        is_first = not Workspace.objects.filter(owner=self.request.user).exists()
        if not is_first:
            from rest_framework.exceptions import ValidationError
            try:
                check_workspace_limit(self.request.user)
            except UsageLimitExceeded as e:
                raise ValidationError({"detail": str(e), "code": "usage_limit_exceeded"})
        ws = serializer.save(owner=self.request.user, is_default=is_first)
        BrandProfile.objects.create(workspace=ws)

        sub = get_or_create_subscription(self.request.user)
        new_count = Workspace.objects.filter(owner=self.request.user).count()
        sync_extra_avatar_quantity(sub, new_count)  # no-op unless on Pro with Stripe already set up

    def perform_destroy(self, instance):
        from billing.usage import get_or_create_subscription
        from billing.stripe_billing import sync_extra_avatar_quantity

        if Workspace.objects.filter(owner=self.request.user).count() <= 1:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You need at least one workspace.")
        instance.delete()

        sub = get_or_create_subscription(self.request.user)
        new_count = Workspace.objects.filter(owner=self.request.user).count()
        sync_extra_avatar_quantity(sub, new_count)


class BrandProfileView(APIView):
    """GET/PATCH the brand profile of ?workspace=<id>."""

    def get_object(self, request):
        ws = get_workspace(request)
        profile, _ = BrandProfile.objects.get_or_create(workspace=ws)
        return profile

    def get(self, request):
        return Response(BrandProfileSerializer(self.get_object(request)).data)

    def patch(self, request):
        profile = self.get_object(request)
        serializer = BrandProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AnalyzeWebsiteView(APIView):
    def post(self, request):
        profile = BrandProfileView().get_object(request)
        try:
            services.summarize_website(profile)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(BrandProfileSerializer(profile).data)


class OnboardingPreviewView(APIView):
    def post(self, request):
        profile = BrandProfileView().get_object(request)
        try:
            out = services.generate_onboarding_preview(profile)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response({"sample_post": out.get("sample_post", ""), "notes": out.get("notes", ""),
                          "disclaimer": "This is a first estimate from what you've shared — refine it anytime from Strategy."})


class AnalyzeToneView(APIView):
    def post(self, request):
        ws = get_workspace(request)
        try:
            profile = services.analyze_tone(ws)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(BrandProfileSerializer(profile).data)


class SuggestTopicsView(APIView):
    def post(self, request):
        ws = get_workspace(request)
        try:
            topics = services.suggest_topics(ws)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response({"topics": topics})


class WorkspaceScopedViewSet(viewsets.ModelViewSet):
    """Shared plumbing for the simple per-workspace lists (reference images, past
    posts, blocked dates, goals): list/detail scoped to workspaces this user owns,
    optionally narrowed to one workspace via ?workspace=, and create requires a
    'workspace' id in the body."""
    model = None

    def get_queryset(self):
        qs = self.model.objects.filter(workspace__owner=self.request.user)
        ws_id = self.request.query_params.get("workspace")
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(workspace=get_workspace(self.request))


class ReferenceImageViewSet(WorkspaceScopedViewSet):
    model = ReferenceImage
    serializer_class = ReferenceImageSerializer


class PastPostViewSet(WorkspaceScopedViewSet):
    model = PastPost
    serializer_class = PastPostSerializer


class BlockedDateViewSet(WorkspaceScopedViewSet):
    model = BlockedDate
    serializer_class = BlockedDateSerializer


class GoalViewSet(WorkspaceScopedViewSet):
    model = Goal
    serializer_class = GoalSerializer

    def create(self, request, *args, **kwargs):
        from billing.usage import check_feature_allowed
        try:
            check_feature_allowed(get_workspace(request), "goals_tracking")
        except UsageLimitExceeded as e:
            return error_response(e)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(workspace=get_workspace(self.request))
