from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from aiengine import services
from aiengine.providers import AIError, error_response
from billing.usage import UsageLimitExceeded
from content.models import Post
from .models import Comment
from .serializers import CommentSerializer


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer

    def get_queryset(self):
        qs = Comment.objects.filter(post__workspace__owner=self.request.user)
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs

    def perform_create(self, serializer):
        post = Post.objects.get(id=self.request.data["post"], workspace__owner=self.request.user)
        serializer.save(post=post)

    @action(detail=True, methods=["post"], url_path="suggest-reply")
    def suggest_reply(self, request, pk=None):
        comment = self.get_object()
        try:
            services.suggest_reply(comment)
        except (AIError, UsageLimitExceeded) as e:
            return error_response(e)
        return Response(CommentSerializer(comment).data)
