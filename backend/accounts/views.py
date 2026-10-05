import logging
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from brand.serializers import WorkspaceSerializer
from .cookies import set_auth_cookies, clear_auth_cookies, REFRESH_COOKIE
from .emailing import send_verification_email
from .models import AccountProfile
from .serializers import RegisterSerializer, LoginSerializer, MeSerializer
from .tokens import email_verification_token
from .turnstile import verify_turnstile

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        if not verify_turnstile(request.data.get("turnstile_token", ""), request.META.get("REMOTE_ADDR", "")):
            return Response({"detail": "Spam check failed — please try again."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        AccountProfile.objects.create(user=user)
        send_verification_email(user)
        refresh = RefreshToken.for_user(user)
        workspace = user.workspaces.first()
        resp = Response({"user": MeSerializer(user).data, "workspace": WorkspaceSerializer(workspace).data}, status=201)
        return set_auth_cookies(resp, str(refresh.access_token), str(refresh))


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        resp = Response({"user": MeSerializer(user).data})
        return set_auth_cookies(resp, str(refresh.access_token), str(refresh))


class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if not raw:
            return Response({"detail": "No refresh cookie."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw)
            access = str(refresh.access_token)
        except TokenError:
            resp = Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            return clear_auth_cookies(resp)
        resp = Response({"ok": True})
        return set_auth_cookies(resp, access)


class LogoutView(APIView):
    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except Exception:
                pass  # blacklist app not installed, or already invalid — cookie clear below still logs them out
        resp = Response({"ok": True})
        return clear_auth_cookies(resp)


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class VerifyEmailView(APIView):
    """No auth required — the link in the email IS the credential, same pattern as password reset."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        uid, token = request.data.get("uid"), request.data.get("token")
        try:
            user = User.objects.get(pk=force_bytes(urlsafe_base64_decode(uid)).decode())
        except Exception:
            return Response({"detail": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)
        if not email_verification_token.check_token(user, token):
            return Response({"detail": "This verification link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = AccountProfile.objects.get_or_create(user=user)
        profile.email_verified = True
        profile.save(update_fields=["email_verified"])
        return Response({"detail": "Email verified."})


class ResendVerificationView(APIView):
    throttle_scope = "auth"

    def post(self, request):
        profile = getattr(request.user, "account_profile", None)
        if profile and profile.email_verified:
            return Response({"detail": "Already verified."})
        sent = send_verification_email(request.user)
        return Response({"detail": "Verification email sent." if sent else "Could not send email — try again shortly."})


class PasswordResetRequestView(APIView):
    """Always returns 200 regardless of whether the email exists — otherwise this
    endpoint becomes a way to check which emails have Postroom accounts."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"
            try:
                send_mail(
                    "Reset your Postroom password",
                    render_to_string("accounts/password_reset_email.txt", {"user": user, "link": link}),
                    settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send password reset email to %s", user.email)
        return Response({"detail": "If that email has an account, a reset link is on its way."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        uid, token, password = request.data.get("uid"), request.data.get("token"), request.data.get("password")
        if not (uid and token and password):
            return Response({"detail": "uid, token and password are all required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=force_bytes(urlsafe_base64_decode(uid)).decode())
        except Exception:
            return Response({"detail": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "This reset link is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(password, user)
        except DjangoValidationError as e:
            return Response({"detail": " ".join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated — log in with your new password."})
