"""Replicate service for AI hair transformation."""

from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from .base import BaseService

logger = logging.getLogger(__name__)


class ReplicateService(BaseService):
    """Service for Replicate AI hair transformation."""

    MODEL_ID = "flux-kontext-apps/change-haircut:48f03523665cabe9a2e832ea9cc2d7c30ad5079cb5f1c1f07890d40596fe1f87"
    
    ALLOWED_HAIRCUTS = [
        "No change", "Random", "Straight", "Wavy", "Curly", "Bob", "Pixie Cut",
        "Layered", "Messy Bun", "High Ponytail", "Low Ponytail", "Braided Ponytail",
        "French Braid", "Dutch Braid", "Fishtail Braid", "Space Buns", "Top Knot",
        "Undercut", "Mohawk", "Crew Cut", "Faux Hawk", "Slicked Back", "Side-Parted",
        "Center-Parted", "Blunt Bangs", "Side-Swept Bangs", "Shag", "Lob",
        "Angled Bob", "A-Line Bob", "Asymmetrical Bob", "Graduated Bob", "Inverted Bob",
        "Layered Shag", "Choppy Layers", "Razor Cut", "Perm", "Ombré", "Straightened",
        "Soft Waves", "Glamorous Waves", "Hollywood Waves", "Finger Waves", "Tousled",
        "Feathered", "Pageboy", "Pigtails", "Pin Curls", "Rollerset", "Twist Out",
        "Bantu Knots", "Dreadlocks", "Cornrows", "Box Braids", "Crochet Braids",
        "Mohawk Fade",
    ]

    STYLE_MAPPINGS = {
        "fade": "Mohawk Fade",
        "modern fade": "Mohawk Fade",
        "buzz": "Crew Cut",
        "buzz cut": "Crew Cut",
        "crew cut": "Crew Cut",
        "short": "Crew Cut",
        "quiff": "Slicked Back",
        "pompadour": "Slicked Back",
        "slick back": "Slicked Back",
        "side part": "Side-Parted",
        "parted": "Side-Parted",
        "undercut": "Undercut",
        "mohawk": "Mohawk",
        "curly": "Curly",
        "textured": "Tousled",
        "messy": "Tousled",
        "wavy": "Wavy",
        "straight": "Straight",
        "bob": "Bob",
        "lob": "Lob",
        "pixie": "Pixie Cut",
        "bun": "Top Knot",
        "layered": "Layered",
        "dreadlocks": "Dreadlocks",
        "center part": "Center-Parted",
    }

    def __init__(self, api_token: Optional[str] = None):
        super().__init__()
        self._api_token = api_token
        self._replicate = None
        self._requests = None

        if api_token:
            try:
                import replicate
                import requests
                import os
                
                os.environ["REPLICATE_API_TOKEN"] = api_token
                self._replicate = replicate
                self._requests = requests
                logger.info("Replicate API configured")
            except ImportError:
                logger.warning("Replicate library not installed")

    def is_configured(self) -> bool:
        """Check if Replicate is properly configured."""
        return self._replicate is not None and self._api_token is not None

    def health_check(self) -> Dict[str, Any]:
        """Return health information about Replicate service."""
        return {
            "configured": self.is_configured(),
            "transformations_today": self._get_usage("transformations"),
        }

    def transform_hair(
        self,
        user_photo_base64: str,
        style_description: str,
        gemini_service: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Transform hair style in a photo.
        
        Args:
            user_photo_base64: Base64 encoded user photo
            style_description: Description of desired hairstyle
            gemini_service: Optional GeminiService for smart style matching
            
        Returns:
            Dictionary with transformation result
        """
        if not user_photo_base64:
            return {"success": False, "error": "User photo required"}
        
        if not style_description:
            return {"success": False, "error": "Style description required"}

        logger.info(f"Starting hair transformation: {style_description}")

        # Try Replicate API first
        if self.is_configured():
            try:
                result = self._transform_with_replicate(
                    user_photo_base64, style_description, gemini_service
                )
                if result.get("success"):
                    return result
            except Exception as e:
                logger.error(f"Replicate transformation error: {e}")

        # Fallback to preview mode
        return self._create_preview(user_photo_base64, style_description)

    def _transform_with_replicate(
        self,
        user_photo_base64: str,
        style_description: str,
        gemini_service: Optional[Any],
    ) -> Dict[str, Any]:
        """Perform transformation using Replicate API."""
        # Clean base64 data
        img_data_raw = user_photo_base64.split(",")[1] if "," in user_photo_base64 else user_photo_base64
        face_data_uri = f"data:image/jpeg;base64,{img_data_raw}"

        # Match style to allowed haircuts
        haircut_name = self._match_style(style_description, gemini_service)
        logger.info(f"Using haircut style: {haircut_name}")

        # Run Replicate model
        logger.info("Calling Replicate API...")
        output = self._replicate.run(
            self.MODEL_ID,
            input={
                "input_image": face_data_uri,
                "haircut": haircut_name,
                "aspect_ratio": "match_input_image",
                "output_format": "png",
                "safety_tolerance": 2,
            },
        )

        # Extract result URL
        result_url = self._extract_result_url(output)
        if not result_url:
            raise Exception("No result URL from model")

        # Download result
        logger.info(f"Downloading result from: {result_url}")
        response = self._requests.get(result_url, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Failed to download: {response.status_code}")

        result_base64 = base64.b64encode(response.content).decode("utf-8")
        original_base64 = img_data_raw

        self._increment_usage("transformations")

        return {
            "success": True,
            "message": f"✨ Real AI hair transformation complete: {style_description}",
            "originalImage": original_base64,
            "resultImage": result_base64,
            "styleApplied": style_description,
            "poweredBy": "Replicate FLUX.1 Kontext (Change-Haircut AI)",
            "note": "This is a real AI transformation!",
        }

    def _match_style(
        self,
        style_description: str,
        gemini_service: Optional[Any],
    ) -> str:
        """Match style description to allowed haircut name."""
        # Try Gemini matching first
        if gemini_service and gemini_service.can_make_call():
            try:
                matched = gemini_service.match_haircut_style(
                    style_description, self.ALLOWED_HAIRCUTS
                )
                if matched in self.ALLOWED_HAIRCUTS:
                    return matched
            except Exception as e:
                logger.warning(f"Gemini matching failed: {e}")

        # Fallback to keyword matching
        style_lower = style_description.lower().strip()
        
        # Check longer phrases first
        sorted_keys = sorted(self.STYLE_MAPPINGS.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key in style_lower:
                return self.STYLE_MAPPINGS[key]

        return "Random"

    def _extract_result_url(self, output: Any) -> Optional[str]:
        """Extract result URL from Replicate output."""
        if isinstance(output, str):
            return output
        if isinstance(output, list) and output:
            return output[0]
        if hasattr(output, "__iter__"):
            try:
                output_list = list(output)
                if output_list:
                    return output_list[0]
            except Exception:
                pass
        return str(output) if output else None

    def _create_preview(
        self,
        user_photo_base64: str,
        style_description: str,
    ) -> Dict[str, Any]:
        """Create preview mode result (image with text overlay)."""
        logger.info("Using preview mode")

        try:
            # Decode image
            if "," in user_photo_base64:
                img_data = base64.b64decode(user_photo_base64.split(",")[1])
            else:
                img_data = base64.b64decode(user_photo_base64)

            img = Image.open(BytesIO(img_data))
            
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            # Add overlay
            if img.mode == "RGB":
                img = img.convert("RGBA")

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            
            width, height = img.size
            overlay_draw.rectangle([(0, height - 70), (width, height)], fill=(0, 0, 0, 200))
            
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")

            # Add text
            draw = ImageDraw.Draw(img)
            text = f"Preview: {style_description}"
            
            font = self._load_font()
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
            except Exception:
                text_width = len(text) * 15

            text_x = max(10, (width - text_width) // 2)
            text_y = max(10, height - 50)

            draw.text((text_x + 2, text_y + 2), text, fill=(0, 0, 0), font=font)
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90, optimize=True)
            result_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            original_base64 = user_photo_base64.split(",")[1] if "," in user_photo_base64 else user_photo_base64

            return {
                "success": True,
                "message": f"✨ Style preview created: {style_description}",
                "originalImage": original_base64,
                "resultImage": result_base64,
                "styleApplied": style_description,
                "poweredBy": "LineUp Preview Mode",
                "note": "This is a preview mode. Configure Replicate for real AI transformations!",
            }

        except Exception as e:
            logger.error(f"Preview creation error: {e}")
            return {
                "success": False,
                "error": f"Failed to create preview: {str(e)}",
            }

    def _load_font(self) -> Any:
        """Load a font for text overlay."""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "arial.ttf",
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, 28)
            except Exception:
                continue
        
        return ImageFont.load_default()
