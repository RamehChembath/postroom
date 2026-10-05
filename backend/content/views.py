from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from aiengine import services
from aiengine.providers import AIError, error_response
from billing.usage import UsageLimitExceeded
from brand.utils import get_workspace
from .models import ContentPlan, PlannedItem, Post
from .serializers import ContentPlanSerializer, PlannedItemSerializer, PostListSerializer, PostDetailSerializer


class ContentPlanViewSet(viewsets.ModelViewSet):
    serializer_class = ContentPlanSerializer

    def get_queryset(self):
        qs = ContentPlan.objects.filter(workspace__owner=self.request.user)
        ws_id = self.request.query_params.get("workspace")
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(workspace=get_workspace(self.request))

    @action(detail=True, methods=["post"], url_path="generate-calendar")
    def generate_calendar(self, request, pk=None):
        plan = self.get_object()
        try:
            services.generate_calendar(plan)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(ContentPlanSerializer(plan).data)

    @action(detail=True, methods=["post"], url_path="approve-items")
    def approve_items(self, request, pk=None):
        """Body: {"approved": [itemId, ...], "rejected": [itemId, ...]}. Approved items get full drafts generated."""
        plan = self.get_object()
        approved_ids = request.data.get("approved", [])
        rejected_ids = request.data.get("rejected", [])
        PlannedItem.objects.filter(plan=plan, id__in=rejected_ids).update(status="rejected")
        items = list(PlannedItem.objects.filter(plan=plan, id__in=approved_ids))
        for item in items:
            item.status = "approved"
            item.save(update_fields=["status"])
        plan.status = "approved"
        plan.save(update_fields=["status"])

        created, failed = [], []
        for item in items:
            try:
                post = services.generate_draft_for_item(item)
                created.append(post.id)
            except AIError:
                failed.append(item.id)
        return Response({"created_post_ids": created, "failed_item_ids": failed})


class PlannedItemViewSet(viewsets.ModelViewSet):
    serializer_class = PlannedItemSerializer

    def get_queryset(self):
        return PlannedItem.objects.filter(plan__workspace__owner=self.request.user)


class PostViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        qs = Post.objects.filter(workspace__owner=self.request.user)
        ws_id = self.request.query_params.get("workspace")
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status__in=status_param.split(","))
        return qs

    def get_serializer_class(self):
        return PostDetailSerializer if self.action == "retrieve" else PostListSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def perform_create(self, serializer):
        serializer.save(workspace=get_workspace(self.request))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Moves a pending draft into the Posting Room."""
        post = self.get_object()
        post.status = "approved"
        if not post.scheduled_at:
            post.scheduled_at = timezone.now()
        post.save(update_fields=["status", "scheduled_at"])
        return Response(PostDetailSerializer(post, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def mark_posted(self, request, pk=None):
        post = self.get_object()
        post.status = "posted"
        post.posted_at = timezone.now()
        post.save(update_fields=["status", "posted_at"])
        return Response(PostDetailSerializer(post, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def predict(self, request, pk=None):
        post = self.get_object()
        try:
            services.predict_potential(post)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(PostDetailSerializer(post, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="suggest-next")
    def suggest_next(self, request, pk=None):
        post = self.get_object()
        try:
            services.suggest_next_step(post)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(PostDetailSerializer(post, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="generate-image")
    def generate_image(self, request, pk=None):
        post = self.get_object()
        brief = request.data.get("brief") or f"A professional, tasteful editorial image illustrating: {post.title or post.text[:120]}"
        try:
            services.generate_post_image(post, brief)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(PostDetailSerializer(post, context={"request": request}).data)


# ---------- Dashboard ----------
from datetime import timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from rest_framework.views import APIView


class DashboardView(APIView):
    def get(self, request):
        ws = get_workspace(request)
        posted = Post.objects.filter(workspace=ws, status="posted")

        totals = posted.aggregate(total_likes=Sum("likes"), total_posts=Count("id"))
        total_comments = sum(p.comments.count() for p in posted)

        daily = (posted.filter(posted_at__gte=timezone.now() - timedelta(days=30))
                 .annotate(day=TruncDate("posted_at")).values("day")
                 .annotate(likes=Sum("likes"), posts=Count("id", distinct=True), comments=Count("comments", distinct=True))
                 .order_by("day"))
        weekly = (posted.filter(posted_at__gte=timezone.now() - timedelta(weeks=12))
                  .annotate(week=TruncWeek("posted_at")).values("week")
                  .annotate(likes=Sum("likes"), posts=Count("id", distinct=True), comments=Count("comments", distinct=True))
                  .order_by("week"))
        monthly = (posted.annotate(month=TruncMonth("posted_at")).values("month")
                   .annotate(likes=Sum("likes"), posts=Count("id", distinct=True), comments=Count("comments", distinct=True))
                   .order_by("month"))

        top = posted.order_by("-likes")[:5]
        worst = posted.exclude(id__in=[p.id for p in top]).order_by("likes")[:3]

        goal = ws.goals.filter(is_active=True).first()
        goal_data = None
        if goal:
            from brand.serializers import GoalSerializer
            goal_data = GoalSerializer(goal).data

        return Response({
            "total_likes": totals["total_likes"] or 0,
            "total_posts": totals["total_posts"] or 0,
            "total_comments": total_comments,
            "avg_likes": round((totals["total_likes"] or 0) / totals["total_posts"], 1) if totals["total_posts"] else 0,
            "daily": list(daily),
            "weekly": list(weekly),
            "monthly": list(monthly),
            "top_posts": PostListSerializer(top, many=True, context={"request": request}).data,
            "lowest_posts": PostListSerializer(worst, many=True, context={"request": request}).data,
            "active_goal": goal_data,
        })


class PerformanceAnalysisView(APIView):
    def post(self, request):
        ws = get_workspace(request)
        try:
            out = services.analyze_performance(ws)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(out)
