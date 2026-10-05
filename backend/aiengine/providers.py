"""
Thin, swappable wrappers around Claude (text/reasoning) and OpenAI (images, and
text as a fallback). All prompt logic lives in prompts.py / services.py — this
file only knows how to make a call and parse a response.
"""
import json
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# USD per 1 million tokens. ILLUSTRATIVE — check Anthropic's and OpenAI's current
# published pricing before relying on these for real billing; they change.
CLAUDE_PRICING_PER_M = {"input": 3.00, "output": 15.00}
OPENAI_TEXT_PRICING_PER_M = {"input": 2.50, "output": 10.00}
OPENAI_IMAGE_COST_FLAT = 0.04  # per image, illustrative — actual cost varies by size/quality


class AIError(RuntimeError):
    """Raised for any provider/parsing failure, with a message safe to show the user."""


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"```json|```", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < 0:
        raise AIError("The AI did not return usable output. Try again.")
    return json.loads(cleaned[start:end + 1])


def claude_json(system: str, user: str, max_tokens: int = 2000) -> tuple[dict, float]:
    """Returns (parsed_json, actual_cost_usd) — cost computed from the real
    input/output token counts Anthropic reports back, not an estimate."""
    if not settings.ANTHROPIC_API_KEY:
        raise AIError("No Anthropic API key configured on the server.")
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        cost = (
            resp.usage.input_tokens / 1_000_000 * CLAUDE_PRICING_PER_M["input"]
            + resp.usage.output_tokens / 1_000_000 * CLAUDE_PRICING_PER_M["output"]
        )
        return _extract_json(text), round(cost, 6)
    except AIError:
        raise
    except Exception as exc:
        logger.exception("Claude call failed")
        raise AIError(f"Claude request failed: {exc}") from exc


def openai_json(system: str, user: str, max_tokens: int = 2000) -> tuple[dict, float]:
    if not settings.OPENAI_API_KEY:
        raise AIError("No OpenAI API key configured on the server.")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=settings.OPENAI_TEXT_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
        )
        cost = (
            resp.usage.prompt_tokens / 1_000_000 * OPENAI_TEXT_PRICING_PER_M["input"]
            + resp.usage.completion_tokens / 1_000_000 * OPENAI_TEXT_PRICING_PER_M["output"]
        )
        return _extract_json(resp.choices[0].message.content), round(cost, 6)
    except AIError:
        raise
    except Exception as exc:
        logger.exception("OpenAI text call failed")
        raise AIError(f"OpenAI request failed: {exc}") from exc


def text_json(system: str, user: str, max_tokens: int = 2000) -> tuple[dict, float]:
    """Routes to whichever provider is configured as TEXT_PROVIDER (default: Claude).
    Returns (parsed_json, actual_cost_usd)."""
    provider = (settings.TEXT_PROVIDER or "claude").lower()
    if provider == "openai":
        return openai_json(system, user, max_tokens)
    return claude_json(system, user, max_tokens)


def generate_image_bytes(prompt: str, size: str = "1024x1024") -> tuple[bytes, float]:
    """Generates an image with OpenAI's image model. Returns (png_bytes, cost_usd) —
    image cost is a flat per-image estimate, not usage-metered the way text is."""
    if not settings.OPENAI_API_KEY:
        raise AIError("No OpenAI API key configured on the server.")
    try:
        import base64
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        resp = client.images.generate(model=settings.OPENAI_IMAGE_MODEL, prompt=prompt, size=size, n=1)
        b64 = resp.data[0].b64_json
        return base64.b64decode(b64), OPENAI_IMAGE_COST_FLAT
    except Exception as exc:
        logger.exception("OpenAI image generation failed")
        raise AIError(f"Image generation failed: {exc}") from exc


def fetch_url_text(url: str, max_chars: int = 6000) -> str:
    """Best-effort fetch of a web page's visible text, for company-site summarization."""
    import urllib.request
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.chunks = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip and data.strip():
                self.chunks.append(data.strip())

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (PostroomBot)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="ignore")
        parser = _TextExtractor()
        parser.feed(html)
        return " ".join(parser.chunks)[:max_chars]
    except Exception as exc:
        logger.warning("Could not fetch %s: %s", url, exc)
        return ""


def error_response(exc):
    """Shared error->HTTP mapping for every AI-calling view: a usage-limit hit is
    402 Payment Required (actionable, upgrade-able), anything else from the
    provider layer is a 502 (upstream failure, not the user's fault)."""
    from rest_framework.response import Response
    from rest_framework import status
    from billing.usage import UsageLimitExceeded
    if isinstance(exc, UsageLimitExceeded):
        return Response({"detail": str(exc), "code": "usage_limit_exceeded"}, status=status.HTTP_402_PAYMENT_REQUIRED)
    return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
