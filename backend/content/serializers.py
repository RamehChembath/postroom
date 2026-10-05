from rest_framework import serializers
from .models import ContentPlan, PlannedItem, Post, PostImage


class PlannedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlannedItem
        fields = ["id", "title", "angle", "item_type", "suggested_date", "date_rationale", "status", "order"]


class ContentPlanSerializer(serializers.ModelSerializer):
    items = PlannedItemSerializer(many=True, read_only=True)

    class Meta:
        model = ContentPlan
        fields = ["id", "subject", "brief", "num_posts", "num_articles", "start_date", "end_date", "status", "created_at", "items"]
        read_only_fields = ["status", "created_at"]


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["id", "image", "prompt", "source", "created_at"]


class PostListSerializer(serializers.ModelSerializer):
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "type", "title", "text", "hashtags", "status", "scheduled_at", "posted_at",
                  "likes", "reach", "predicted_score", "comment_count", "image", "created_at"]

    def get_image(self, obj):
        img = obj.images.order_by("-created_at").first()
        if not img:
            return None
        request = self.context.get("request")
        url = img.image.url
        return request.build_absolute_uri(url) if request else url


class PostDetailSerializer(PostListSerializer):
    images = PostImageSerializer(many=True, read_only=True)

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ["images", "predicted_reason", "predicted_tip",
                                                     "next_step_suggestion", "next_step_at", "plan", "planned_item"]
