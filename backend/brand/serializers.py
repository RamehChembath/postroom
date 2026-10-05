from rest_framework import serializers
from .models import Workspace, BrandProfile, ReferenceImage, PastPost, BlockedDate, Goal


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "name", "persona_type", "is_default", "created_at"]
        read_only_fields = ["created_at"]


class BrandProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandProfile
        fields = [
            "id", "company_name", "company_website", "website_summary",
            "industry", "target_audience", "core_topics", "voice_notes",
            "tone_summary", "tone_traits", "tone_language", "tone_sample_post",
            "tone_analyzed_at", "tone_posts_analyzed", "onboarding_completed",
        ]
        read_only_fields = [
            "website_summary", "tone_summary", "tone_traits", "tone_language",
            "tone_sample_post", "tone_analyzed_at", "tone_posts_analyzed",
        ]


class ReferenceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceImage
        fields = ["id", "image", "note", "created_at"]
        read_only_fields = ["created_at"]


class PastPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = PastPost
        fields = ["id", "text", "likes", "posted_on", "created_at"]
        read_only_fields = ["created_at"]


class BlockedDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockedDate
        fields = ["id", "date", "reason"]


class GoalSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = ["id", "title", "metric", "target_value", "period", "start_date", "end_date", "is_active", "created_at", "progress"]
        read_only_fields = ["created_at", "progress"]

    def get_progress(self, obj):
        from content.models import Post
        qs = Post.objects.filter(workspace=obj.workspace, status="posted", posted_at__date__range=(obj.start_date, obj.end_date))
        if obj.metric == "likes":
            current = sum(p.likes for p in qs)
        elif obj.metric == "comments":
            current = sum(p.comments.count() for p in qs)
        else:
            current = qs.count()
        return {"current": current, "target": obj.target_value, "pct": round(min(100, current / obj.target_value * 100), 1) if obj.target_value else 0}
