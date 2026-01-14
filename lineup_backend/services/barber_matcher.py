"""AI-powered barber matching service that finds barbers specializing in specific haircut styles."""

import logging
import time
from typing import Dict, List, Any, Optional
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class BarberMatcher:
    """Matches barbers to recommended haircut styles using AI analysis."""
    
    def __init__(self, gemini_model=None):
        """
        Initialize the barber matcher.
        
        Args:
            gemini_model: Optional Gemini AI model for review analysis
        """
        self.model = gemini_model
        self._cache = {}  # Cache for style analysis results
        self._cache_ttl = 3600  # 1 hour cache
    
    def build_search_keywords(self, recommended_styles: List[str]) -> str:
        """
        Build enhanced keyword string for Places API search.
        
        Args:
            recommended_styles: List of recommended haircut style names
            
        Returns:
            Space-separated keywords string optimized for Places API
        """
        base_keywords = "barber barbershop mens haircut"
        
        if not recommended_styles or not any(recommended_styles):
            return base_keywords
        
        style_keywords = []
        for style in recommended_styles:
            if style and isinstance(style, str):
                style_lower = style.lower().strip()
                if style_lower:
                    # Add full style name
                    style_keywords.append(style_lower)
                    # Extract individual words (e.g., "Modern Fade" -> ["modern", "fade"])
                    words = [w for w in style_lower.split() if len(w) > 2]
                    style_keywords.extend(words)
        
        # Deduplicate and limit to avoid API issues
        unique_keywords = list(dict.fromkeys(style_keywords))[:8]
        all_keywords = [base_keywords] + unique_keywords
        
        return " ".join(all_keywords)
    
    def analyze_barber_reviews(
        self, 
        barber_name: str, 
        reviews: List[Dict[str, Any]], 
        recommended_styles: List[str]
    ) -> Dict[str, Any]:
        """
        Use Gemini AI to analyze reviews and determine style expertise.
        
        Args:
            barber_name: Name of the barbershop
            reviews: List of review objects with 'text' field
            recommended_styles: List of haircut styles to match
            
        Returns:
            Dict with match scores and evidence
        """
        if not self.model or not recommended_styles or not reviews:
            return {"overall_match_score": 0.0, "matches": []}
        
        # Check cache
        cache_key = f"{barber_name}:{','.join(sorted(recommended_styles))}"
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached['timestamp']) < self._cache_ttl:
            logger.info(f"Using cached analysis for {barber_name}")
            return cached['data']
        
        # Combine top reviews (limit text to avoid token limits)
        reviews_text = []
        for review in reviews[:5]:
            text = review.get('text', '').strip()
            if text:
                reviews_text.append(text[:300])  # Limit each review to 300 chars
        
        if not reviews_text:
            return {"overall_match_score": 0.0, "matches": []}
        
        combined_reviews = " | ".join(reviews_text)[:2000]  # Max 2000 chars total
        styles_str = ", ".join(recommended_styles)
        
        prompt = f"""Analyze these barbershop reviews to determine expertise in specific haircut styles.

BARBERSHOP: {barber_name}
STYLES TO MATCH: {styles_str}
REVIEWS: {combined_reviews}

Determine if this barbershop specializes in the given styles based on the reviews.

Return ONLY valid JSON (no markdown, no code blocks):
{{
    "overall_match_score": 0.0-1.0,
    "matches": [
        {{
            "style": "style name",
            "confidence": 0.0-1.0,
            "evidence": "brief quote or reason"
        }}
    ]
}}

Rules:
- overall_match_score: 0.0 (no evidence) to 1.0 (strong evidence)
- Include a match entry for each style found in reviews
- Evidence should be a brief quote or reason (max 50 chars)
- Return empty matches array if no style mentions found
"""
        
        try:
            logger.info(f"Analyzing reviews for {barber_name} with Gemini")
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response (remove markdown if present)
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.rfind("```")
                if end > start:
                    response_text = response_text[start:end].strip()
            elif "```" in response_text:
                response_text = response_text.replace("```", "").strip()
            
            result = json.loads(response_text)
            
            # Validate and normalize
            if not isinstance(result, dict):
                raise ValueError("Invalid JSON structure")
            
            analysis = {
                "overall_match_score": max(0.0, min(1.0, float(result.get("overall_match_score", 0.0)))),
                "matches": result.get("matches", [])
            }
            
            # Cache result
            self._cache[cache_key] = {
                'data': analysis,
                'timestamp': time.time()
            }
            
            logger.info(f"Analysis for {barber_name}: score={analysis['overall_match_score']:.2f}, matches={len(analysis['matches'])}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing reviews for {barber_name}: {e}")
            return {"overall_match_score": 0.0, "matches": []}
    
    def calculate_style_relevance(
        self,
        barber: Dict[str, Any],
        recommended_styles: List[str],
        style_analysis: Dict[str, Any]
    ) -> float:
        """
        Calculate overall relevance score for a barber based on style match.
        
        Args:
            barber: Barber info dict
            recommended_styles: List of recommended styles
            style_analysis: Result from analyze_barber_reviews
            
        Returns:
            Relevance score from 0.0 to 1.0
        """
        if not recommended_styles:
            return 0.0
        
        score = 0.0
        name_lower = barber.get('name', '').lower()
        
        # Weight 1: Barbershop name contains style keywords (30%)
        name_match_score = 0.0
        for style in recommended_styles:
            if not style:
                continue
            style_words = [w.lower() for w in style.split() if len(w) > 2]
            for word in style_words:
                if word in name_lower:
                    name_match_score += 0.3 / len(recommended_styles)
                    break
        score += min(name_match_score, 0.3)
        
        # Weight 2: AI review analysis (50%)
        if style_analysis:
            ai_score = style_analysis.get('overall_match_score', 0.0)
            score += ai_score * 0.5
        
        # Weight 3: Review text keyword matching (20%)
        reviews = barber.get('reviews', [])
        if reviews:
            reviews_text = " ".join([r.get('text', '').lower() for r in reviews[:10]])
            keyword_match_score = 0.0
            for style in recommended_styles:
                if not style:
                    continue
                style_words = [w.lower() for w in style.split() if len(w) > 2]
                for word in style_words:
                    if word in reviews_text:
                        keyword_match_score += 0.2 / len(recommended_styles)
                        break
            score += min(keyword_match_score, 0.2)
        
        return min(score, 1.0)
    
    def rank_barbers(
        self,
        barbers: List[Dict[str, Any]],
        recommended_styles: List[str],
        use_ai_analysis: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank barbers by relevance to recommended styles.
        
        Args:
            barbers: List of barber info dicts
            recommended_styles: List of recommended haircut styles
            use_ai_analysis: Whether to use AI review analysis (slower but more accurate)
            
        Returns:
            Sorted list of barbers with added relevance scores
        """
        if not recommended_styles or not any(recommended_styles):
            # No specific styles - just sort by rating
            barbers.sort(
                key=lambda x: x.get('rating', 0) * min(x.get('user_ratings_total', 0), 100) / 100,
                reverse=True
            )
            return barbers
        
        logger.info(f"Ranking {len(barbers)} barbers for styles: {recommended_styles}")
        
        # Use parallel processing for AI analysis to reduce latency
        if use_ai_analysis and self.model:
            # Process barbers in parallel with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {}
                for barber in barbers:
                    if barber.get('reviews'):
                        future = executor.submit(
                            self.analyze_barber_reviews,
                            barber.get('name', ''),
                            barber.get('reviews', []),
                            recommended_styles
                        )
                        futures[future] = barber
                
                # Collect results as they complete
                for future in as_completed(futures):
                    barber = futures[future]
                    try:
                        barber['style_analysis'] = future.result(timeout=5)
                    except Exception as e:
                        logger.error(f"Analysis failed for {barber.get('name')}: {e}")
                        barber['style_analysis'] = {}
        
        # Calculate relevance for each barber
        for barber in barbers:
            style_analysis = barber.get('style_analysis', {})
            
            relevance = self.calculate_style_relevance(
                barber,
                recommended_styles,
                style_analysis
            )
            
            barber['style_relevance_score'] = relevance
            
            # Calculate composite score (70% relevance, 30% rating)
            rating_score = barber.get('rating', 0) * min(barber.get('user_ratings_total', 0), 100) / 100
            barber['composite_score'] = (relevance * 0.7) + (rating_score / 5.0 * 0.3)
        
        # Sort by composite score
        barbers.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        # Log top matches
        if barbers:
            top = barbers[0]
            logger.info(f"Top match: {top.get('name')} (relevance={top.get('style_relevance_score', 0):.2f}, rating={top.get('rating', 0):.1f})")
        
        return barbers
    
    def clear_cache(self):
        """Clear the analysis cache."""
        self._cache.clear()
        logger.info("Cleared barber matcher cache")

