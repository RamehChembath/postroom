from rest_framework import serializers
from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "post", "person_name", "person_title", "text", "reply", "reply_generated_at", "created_at"]
        read_only_fields = ["reply", "reply_generated_at", "created_at"]
