"""AI Analysis endpoints."""

import base64
import json
import logging
from io import BytesIO

from flask import Blueprint, request
from PIL import Image

from lineup_backend.utils import cors_response, handle_options, api_response

logger = logging.getLogger(__name__)

analyze_bp = Blueprint('analyze', __name__)


def get_mock_analysis_data():
    """Return mock analysis data when AI is unavailable."""
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
            }
        ]
    }


@analyze_bp.route('/analyze', methods=['POST', 'OPTIONS'])
@handle_options("POST, OPTIONS")
def analyze():
    """
    Analyze uploaded photo and provide haircut recommendations.
    Uses Gemini AI when available, falls back to mock data.
    """
    import os
    
    logger.info("ANALYZE endpoint called")
    
    # Try to import and use Gemini
    model = None
    try:
        import google.generativeai as genai
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        logger.warning(f"Gemini not available: {e}")
    
    if not model:
        logger.info("Using mock data (Gemini not configured)")
        return cors_response(get_mock_analysis_data())
    
    try:
        data = request.get_json(force=True)
        
        # Extract image data from request
        try:
            payload = data.get("payload", {})
            contents = payload.get("contents", [{}])[0]
            parts = contents.get("parts", [])
            
            if len(parts) < 2:
                raise ValueError("No image data provided")
            
            image_data = parts[1].get("inlineData", {})
            base64_image = image_data.get("data", "")
            
            if not base64_image:
                raise ValueError("Empty image data")
            
        except (KeyError, IndexError) as e:
            raise ValueError(f"Invalid request format: {str(e)}")
        
        # Decode and validate image
        try:
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            raise ValueError(f"Invalid image data: {str(e)}")
        
        # Create analysis prompt
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

        # Call Gemini API
        try:
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return cors_response(get_mock_analysis_data())
        
        # Clean and parse response
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.rfind("```")
            if end > start:
                response_text = response_text[start:end].strip()
        
        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini response, using mock data")
            return cors_response(get_mock_analysis_data())
        
        # Validate response structure
        if "analysis" not in analysis_data or "recommendations" not in analysis_data:
            return cors_response(get_mock_analysis_data())
        
        return cors_response(analysis_data)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return api_response(error=str(e), status=400)
    except Exception as e:
        logger.error(f"Error in analyze endpoint: {str(e)}")
        return cors_response(get_mock_analysis_data())

