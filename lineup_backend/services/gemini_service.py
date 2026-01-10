"""Gemini AI service for image analysis and content moderation."""

from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google's Gemini AI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.model = None
        self._usage_count = 0
        self._daily_limit = 50
        
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("Gemini API configured successfully")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")
    
    @property
    def is_configured(self) -> bool:
        """Check if Gemini is properly configured."""
        return self.model is not None
    
    def can_make_call(self) -> bool:
        """Check if we can make an API call (within daily limit)."""
        return self._usage_count < self._daily_limit
    
    def _increment_usage(self) -> None:
        """Track API usage."""
        self._usage_count += 1
    
    def reset_daily_usage(self) -> None:
        """Reset daily usage counter."""
        self._usage_count = 0
    
    def analyze_face_and_hair(self, image: Image.Image) -> dict:
        """
        Analyze a face image and provide haircut recommendations.
        
        Args:
            image: PIL Image object of the user's face
            
        Returns:
            Dictionary with analysis and recommendations
        """
        if not self.is_configured:
            logger.warning("Gemini not configured, returning mock data")
            return self._get_mock_analysis()
        
        if not self.can_make_call():
            logger.warning("Gemini daily limit reached, returning mock data")
            return self._get_mock_analysis()
        
        prompt = """You are an expert hairstylist and facial analysis AI. Analyze this person's face and hair in the photo and provide personalized haircut recommendations.

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
        
        try:
            self._increment_usage()
            response = self.model.generate_content([prompt, image])
            response_text = response.text.strip()
            
            # Clean markdown formatting
            response_text = self._clean_json_response(response_text)
            
            analysis_data = json.loads(response_text)
            
            # Validate response structure
            if "analysis" not in analysis_data or "recommendations" not in analysis_data:
                logger.warning("Invalid response structure from Gemini")
                return self._get_mock_analysis()
            
            return analysis_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return self._get_mock_analysis()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._get_mock_analysis()
    
    def moderate_image(self, image_bytes: bytes) -> Tuple[bool, Optional[str]]:
        """
        Moderate image content for explicit or inappropriate content.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Tuple of (is_approved, rejection_reason)
        """
        if not self.is_configured:
            logger.warning("Gemini not available, skipping moderation (permissive mode)")
            return (True, None)
        
        try:
            image = Image.open(BytesIO(image_bytes))
            
            moderation_prompt = """Analyze this image and determine:
1. Is there any explicit, adult, violent, or inappropriate content? (yes/no)
2. Is this image related to hair, haircuts, hairstyles, or barber/stylist work? (yes/no)

Respond with ONLY a JSON object in this exact format (no markdown, no explanation):
{
    "explicit_content": true/false,
    "hair_related": true/false,
    "confidence": "high" | "medium" | "low"
}

If explicit_content is true, the image must be rejected.
If hair_related is false, the image must be rejected as it's not relevant to a hair/barber community."""
            
            self._increment_usage()
            response = self.model.generate_content([moderation_prompt, image])
            response_text = self._clean_json_response(response.text.strip())
            
            moderation_result = json.loads(response_text)
            
            explicit_content = moderation_result.get("explicit_content", False)
            hair_related = moderation_result.get("hair_related", False)
            
            if explicit_content:
                logger.warning("Content moderation: Rejected - Explicit content detected")
                return (False, "Your image contains inappropriate or explicit content and cannot be posted.")
            
            if not hair_related:
                logger.warning("Content moderation: Rejected - Not hair-related")
                return (False, "Your image must be related to hair, haircuts, or hairstyles. Please post hair-related content only.")
            
            logger.info("Content moderation: Approved")
            return (True, None)
            
        except Exception as e:
            logger.error(f"Error in content moderation: {e}")
            # Permissive fallback
            return (True, None)
    
    def match_haircut_style(self, style_description: str, allowed_styles: list) -> str:
        """
        Use Gemini to match a style description to an allowed style name.
        
        Args:
            style_description: User's description of desired style
            allowed_styles: List of allowed style names
            
        Returns:
            Best matching style name from allowed list
        """
        if not self.is_configured:
            return "Random"
        
        prompt = f"""You are a professional hairstylist matching haircut descriptions to specific style names.

TASK: Match this haircut description to the BEST option from the allowed list below.

HAIRCUT DESCRIPTION: "{style_description}"

ALLOWED STYLES (choose ONE exact match):
{', '.join(allowed_styles)}

CRITICAL: Return ONLY the exact name from the list above. No explanations, no quotes, just the exact name."""
        
        try:
            response = self.model.generate_content(prompt)
            gemini_match = response.text.strip().strip('"').strip("'").strip('`')
            gemini_match = gemini_match.split('\n')[0].strip()
            gemini_match = gemini_match.replace('**', '').replace('*', '')
            
            if gemini_match in allowed_styles:
                return gemini_match
            
            # Fuzzy matching fallback
            gemini_lower = gemini_match.lower()
            for allowed in allowed_styles:
                if gemini_lower == allowed.lower() or gemini_lower in allowed.lower():
                    return allowed
            
            return "Random"
            
        except Exception as e:
            logger.warning(f"Gemini matching failed: {e}")
            return "Random"
    
    @staticmethod
    def _clean_json_response(text: str) -> str:
        """Remove markdown formatting from JSON response."""
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.rfind("```")
            if end > start:
                return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.rfind("```")
            if end > start:
                return text[start:end].strip()
        return text
    
    @staticmethod
    def _get_mock_analysis() -> dict:
        """Return mock analysis data when API is unavailable."""
        return {
            "analysis": {
                "faceShape": "oval",
                "hairTexture": "wavy",
                "hairColor": "brown",
                "estimatedGender": "male",
                "estimatedAge": "25-30"
            },
            "recommendations": [
                {
                    "styleName": "Modern Fade",
                    "description": "A contemporary take on the classic fade with textured top",
                    "reason": "Complements oval face shapes perfectly"
                },
                {
                    "styleName": "Textured Quiff",
                    "description": "Voluminous style swept upward for a bold look",
                    "reason": "Works beautifully with wavy hair texture"
                },
                {
                    "styleName": "Classic Side Part",
                    "description": "Timeless and professional with clean lines",
                    "reason": "Enhances facial features and adds sophistication"
                },
                {
                    "styleName": "Messy Crop",
                    "description": "Effortlessly cool with natural texture",
                    "reason": "Low maintenance yet stylish option"
                },
                {
                    "styleName": "Short Buzz",
                    "description": "Clean, minimal, and masculine",
                    "reason": "Highlights facial structure beautifully"
                },
                {
                    "styleName": "Undercut",
                    "description": "Edgy style with shaved sides and longer top",
                    "reason": "Modern and versatile for most face shapes"
                }
            ]
        }
