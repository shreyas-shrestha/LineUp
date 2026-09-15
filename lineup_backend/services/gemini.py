"""Gemini integration: face/hair analysis, image moderation, haircut matching.

Every public method degrades gracefully: when the key is missing, the daily
budget is spent or the API fails, callers get ``None`` (or a permissive answer
for moderation) and decide how to fall back. Nothing here raises to routes.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from lineup_backend.services.quota import DailyQuota

logger = logging.getLogger(__name__)

GEMINI_TIMEOUT_SECONDS = 45  # a hung provider call must not hold a worker until gunicorn kills it

ANALYSIS_PROMPT = """You are an expert hairstylist and facial analysis assistant. Analyze this person's face and hair in the photo and provide personalized haircut recommendations.

IMPORTANT: Return ONLY a valid JSON response with NO additional text, NO markdown formatting, NO code blocks.

Return this EXACT JSON structure:
{
    "analysis": {
        "faceShape": "[one of: oval, round, square, heart, oblong, diamond, triangle]",
        "hairTexture": "[one of: straight, wavy, curly, coily, kinky]",
        "hairColor": "[one of: black, dark-brown, brown, light-brown, blonde, red, gray, white, other]",
        "estimatedGender": "[one of: male, female, non-binary]",
        "estimatedAge": "[one of: under-20, 20-25, 25-30, 30-35, 35-40, 40-45, 45-50, 50-55, 55-60, over-60]"
    },
    "recommendations": [
        {
            "styleName": "[Specific haircut name]",
            "description": "[2-3 sentence description of the haircut style and how it's achieved]",
            "reason": "[1-2 sentences explaining why this works for their specific face shape, hair texture, and features]"
        }
    ]
}

Provide exactly 6 haircut recommendations that would work best for this person's features."""

MODERATION_PROMPT = """Analyze this image and determine:
1. Is there any explicit, adult, violent, or inappropriate content? (yes/no)
2. Is this image related to hair, haircuts, hairstyles, or barber/stylist work? (yes/no)

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{
    "explicit_content": true/false,
    "hair_related": true/false,
    "confidence": "high" | "medium" | "low"
}"""

REJECT_EXPLICIT = "Your image contains inappropriate or explicit content and cannot be posted."
REJECT_OFF_TOPIC = "Your image must be related to hair, haircuts, or hairstyles. Please post hair-related content only."


def parse_json_block(text: Optional[str]) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from model output that may include code fences."""
    if not text:
        return None
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            result = json.loads(cleaned[start : end + 1])
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def mock_analysis(reason: str = "gemini_not_configured") -> Dict[str, Any]:
    """Deterministic analysis used when Gemini is unavailable. ``mock`` is True."""
    return {
        "mock": True,
        "source": "mock",
        "reason": reason,
        "analysis": {
            "faceShape": "oval",
            "hairTexture": "wavy",
            "hairColor": "brown",
            "estimatedGender": "male",
            "estimatedAge": "25-30",
        },
        "recommendations": [
            {
                "styleName": "Modern Fade",
                "description": "A contemporary take on the classic fade with a textured top.",
                "reason": "Complements oval face shapes.",
            },
            {
                "styleName": "Textured Quiff",
                "description": "Voluminous style swept upward for a bold look.",
                "reason": "Works well with wavy hair texture.",
            },
            {
                "styleName": "Classic Side Part",
                "description": "Timeless and professional with clean lines.",
                "reason": "Enhances facial features and adds structure.",
            },
            {
                "styleName": "Messy Crop",
                "description": "Short, textured cut with a deliberately tousled finish.",
                "reason": "Low maintenance while keeping natural texture.",
            },
            {
                "styleName": "Short Buzz",
                "description": "Clean, minimal, and easy to maintain.",
                "reason": "Highlights facial structure.",
            },
            {
                "styleName": "Undercut",
                "description": "Short sides with a longer top for contrast.",
                "reason": "Adds definition to an oval face.",
            },
        ],
    }


class GeminiService:
    """Thin wrapper around ``google.generativeai`` with a daily budget."""

    def __init__(self, api_key: Optional[str], model_name: str, quota: DailyQuota, model: Any = None) -> None:
        self.model_name = model_name
        self.quota = quota
        self.model = model if model is not None else self._build_model(api_key, model_name)

    @staticmethod
    def _build_model(api_key: Optional[str], model_name: str) -> Any:
        if not api_key:
            logger.warning("GEMINI_API_KEY not set: analysis and moderation use mock responses")
            return None
        try:
            import google.generativeai as genai
        except ImportError:
            logger.warning("google-generativeai not installed: Gemini disabled")
            return None
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            logger.info("Gemini configured (model=%s)", model_name)
            return model
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini configuration failed: %s", type(exc).__name__)
            return None

    @property
    def available(self) -> bool:
        return self.model is not None

    def status(self) -> str:
        if not self.available:
            return "not_configured"
        if not self.quota.can_call():
            return "quota_exhausted"
        return "ready"

    def generate(self, parts: List[Any]) -> Optional[str]:
        """Run the model. Returns the text or None on any failure."""
        if not self.available or not self.quota.can_call():
            return None
        self.quota.record()
        try:
            response = self.model.generate_content(parts, request_options={"timeout": GEMINI_TIMEOUT_SECONDS})
            text = getattr(response, "text", None)
            return text.strip() if isinstance(text, str) else None
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini call failed: %s: %s", type(exc).__name__, exc)
            return None

    def generate_text(self, prompt: str) -> Optional[str]:
        return self.generate([prompt])

    def analyze_face(self, image: Any) -> Optional[Dict[str, Any]]:
        """Return ``{"analysis": {...}, "recommendations": [...]}`` or None."""
        result = parse_json_block(self.generate([ANALYSIS_PROMPT, image]))
        if not result:
            return None
        analysis, recommendations = result.get("analysis"), result.get("recommendations")
        if not isinstance(analysis, dict) or not isinstance(recommendations, list) or not recommendations:
            logger.warning("Gemini analysis had an unexpected shape; ignoring")
            return None
        return {"analysis": analysis, "recommendations": recommendations}

    def moderate_image(self, image: Any) -> Tuple[bool, Optional[str]]:
        """Return (approved, rejection_reason). Permissive when unavailable."""
        result = parse_json_block(self.generate([MODERATION_PROMPT, image]))
        if not result:
            return True, None
        if bool(result.get("explicit_content")):
            return False, REJECT_EXPLICIT
        if not bool(result.get("hair_related", True)):
            return False, REJECT_OFF_TOPIC
        return True, None

    def match_haircut(self, description: str, allowed: List[str]) -> Optional[str]:
        """Map a free-text style to one of ``allowed`` (exact or fuzzy)."""
        prompt = (
            "Match this haircut description to the BEST option from this exact list:\n\n"
            f'DESCRIPTION: "{description}"\n\n'
            f"ALLOWED OPTIONS (choose ONE exact match):\n{', '.join(allowed)}\n\n"
            "Return ONLY the exact name from the list above. No explanations."
        )
        text = self.generate_text(prompt)
        if not text:
            return None
        candidate = text.split("\n")[0].strip().strip('"').strip("'").replace("*", "").replace("`", "").strip()
        if candidate in allowed:
            return candidate
        lowered = candidate.lower()
        for option in allowed:
            option_lower = option.lower()
            if lowered == option_lower or lowered in option_lower or option_lower in lowered:
                return option
        return None
