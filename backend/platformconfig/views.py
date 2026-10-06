from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from aiengine import providers
from .models import AISettings


def _mask(key: str) -> str:
    if not key:
        return ""
    return f"{key[:7]}{'•' * 12}{key[-4:]}" if len(key) > 11 else "•" * len(key)


class AISettingsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        obj = AISettings.load()
        return Response({
            "anthropic_configured": bool(providers.get_anthropic_key()),
            "anthropic_masked": _mask(obj.anthropic_api_key) if obj.anthropic_api_key else ("env configured" if providers.get_anthropic_key() else ""),
            "openai_configured": bool(providers.get_openai_key()),
            "openai_masked": _mask(obj.openai_api_key) if obj.openai_api_key else ("env configured" if providers.get_openai_key() else ""),
            "default_claude_model": obj.default_claude_model,
            "effective_claude_model": providers.get_claude_model(),
            "updated_at": obj.updated_at,
        })

    def patch(self, request):
        obj = AISettings.load()
        # Blank = "leave the stored value as-is" (so the masked field doesn't
        # accidentally wipe a saved key when the form resubmits unchanged).
        if request.data.get("anthropic_api_key"):
            obj.anthropic_api_key = request.data["anthropic_api_key"]
        if request.data.get("openai_api_key"):
            obj.openai_api_key = request.data["openai_api_key"]
        if "default_claude_model" in request.data:
            obj.default_claude_model = request.data["default_claude_model"] or ""
        obj.save()
        return self.get(request)


class TestAIConnectionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        provider = request.data.get("provider", "anthropic")
        try:
            if provider == "openai":
                out, _ = providers.openai_json("Reply with JSON only.", 'Return {"ok": true}', max_tokens=20)
            else:
                out, _ = providers.claude_json("Reply with JSON only.", 'Return {"ok": true}', max_tokens=20)
            return Response({"success": True, "detail": "Connection works."})
        except providers.AIError as e:
            return Response({"success": False, "detail": str(e)}, status=status.HTTP_200_OK)
