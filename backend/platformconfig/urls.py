from django.urls import path
from .views import AISettingsView, TestAIConnectionView

urlpatterns = [
    path("ai-settings/", AISettingsView.as_view(), name="platform-ai-settings"),
    path("ai-settings/test/", TestAIConnectionView.as_view(), name="platform-ai-settings-test"),
]
