from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from billing.models import Subscription
from brand.models import Workspace, BrandProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["email", "password", "full_name"]

    def validate_email(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        full_name = validated_data.pop("full_name", "")
        user = User.objects.create_user(
            username=validated_data["email"], email=validated_data["email"], password=validated_data["password"],
            first_name=full_name[:150],
        )
        ws = Workspace.objects.create(owner=user, name=full_name or "Myself", persona_type="individual", is_default=True)
        BrandProfile.objects.create(workspace=ws)
        Subscription.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Incorrect email or password.")
        attrs["user"] = user
        return attrs


class MeSerializer(serializers.ModelSerializer):
    email_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "email_verified", "is_staff"]

    def get_email_verified(self, user):
        profile = getattr(user, "account_profile", None)
        return bool(profile and profile.email_verified)
