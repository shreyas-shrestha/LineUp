"""Ranks barbershops by how well they match recommended haircut styles.

Uses shop names, review text and (optionally) Gemini review analysis. The
``generate_text`` callable is injected so this module stays free of SDK code.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from lineup_backend.services.gemini import parse_json_block

logger = logging.getLogger(__name__)

TextGenerator = Callable[[str], Optional[str]]


class BarberMatcher:
    MAX_CACHE_ENTRIES = 500  # review analyses are keyed per shop+styles; keep the process bounded

    def __init__(self, generate_text: Optional[TextGenerator] = None, cache_ttl: int = 3600) -> None:
        self.generate_text = generate_text
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = cache_ttl
        # rank_barbers() fans out over a thread pool, so every cache touch is locked.
        self._cache_lock = threading.Lock()

    def _recall(self, key: str) -> Optional[Dict[str, Any]]:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry and (time.time() - entry["timestamp"]) < self._cache_ttl:
                return entry["data"]
            return None

    def _remember(self, key: str, data: Dict[str, Any]) -> None:
        now = time.time()
        with self._cache_lock:
            if len(self._cache) >= self.MAX_CACHE_ENTRIES:
                for stale in [k for k, v in self._cache.items() if now - v["timestamp"] >= self._cache_ttl]:
                    del self._cache[stale]
                while len(self._cache) >= self.MAX_CACHE_ENTRIES:
                    del self._cache[min(self._cache, key=lambda k: self._cache[k]["timestamp"])]
            self._cache[key] = {"data": data, "timestamp": now}

    def build_search_keywords(self, recommended_styles: List[str]) -> str:
        base_keywords = "barber barbershop mens haircut"
        if not recommended_styles:
            return base_keywords
        style_keywords: List[str] = []
        for style in recommended_styles:
            if not isinstance(style, str):
                continue
            style_lower = style.lower().strip()
            if style_lower:
                style_keywords.append(style_lower)
                style_keywords.extend(w for w in style_lower.split() if len(w) > 2)
        unique = list(dict.fromkeys(style_keywords))[:8]
        return " ".join([base_keywords] + unique)

    def analyze_barber_reviews(self, barber_name: str, reviews: List[Dict[str, Any]], styles: List[str]) -> Dict[str, Any]:
        empty = {"overall_match_score": 0.0, "matches": []}
        if not self.generate_text or not styles or not reviews:
            return empty

        cache_key = f"{barber_name}:{','.join(sorted(styles))}"
        cached = self._recall(cache_key)
        if cached is not None:
            return cached

        snippets = [r.get("text", "").strip()[:300] for r in reviews[:5] if r.get("text", "").strip()]
        if not snippets:
            return empty

        prompt = (
            "Analyze these barbershop reviews to determine expertise in specific haircut styles.\n\n"
            f"BARBERSHOP: {barber_name}\nSTYLES TO MATCH: {', '.join(styles)}\n"
            f"REVIEWS: {' | '.join(snippets)[:2000]}\n\n"
            "Return ONLY valid JSON (no markdown):\n"
            '{"overall_match_score": 0.0-1.0, "matches": [{"style": "style name", "confidence": 0.0-1.0, "evidence": "brief reason"}]}\n'
            "Rules: overall_match_score 0.0 (no evidence) to 1.0 (strong evidence); empty matches if none."
        )
        result = parse_json_block(self.generate_text(prompt))
        if not result:
            return empty
        try:
            score = max(0.0, min(1.0, float(result.get("overall_match_score", 0.0))))
        except (TypeError, ValueError):
            score = 0.0
        matches = result.get("matches") if isinstance(result.get("matches"), list) else []
        analysis = {"overall_match_score": score, "matches": matches}
        self._remember(cache_key, analysis)
        return analysis

    @staticmethod
    def calculate_style_relevance(barber: Dict[str, Any], styles: List[str], style_analysis: Dict[str, Any]) -> float:
        if not styles:
            return 0.0
        score = 0.0
        name_lower = barber.get("name", "").lower()

        name_match = 0.0
        for style in styles:
            words = [w.lower() for w in style.split() if len(w) > 2]
            if any(w in name_lower for w in words):
                name_match += 0.3 / len(styles)
        score += min(name_match, 0.3)

        if style_analysis:
            score += float(style_analysis.get("overall_match_score", 0.0)) * 0.5

        reviews_text = " ".join(r.get("text", "").lower() for r in barber.get("reviews", [])[:10])
        if reviews_text:
            keyword_match = 0.0
            for style in styles:
                words = [w.lower() for w in style.split() if len(w) > 2]
                if any(w in reviews_text for w in words):
                    keyword_match += 0.2 / len(styles)
            score += min(keyword_match, 0.2)
        return min(score, 1.0)

    @staticmethod
    def rating_score(barber: Dict[str, Any]) -> float:
        return float(barber.get("rating", 0) or 0) * min(int(barber.get("user_ratings_total", 0) or 0), 100) / 100

    def rank_barbers(self, barbers: List[Dict[str, Any]], styles: List[str], use_ai_analysis: bool = True) -> List[Dict[str, Any]]:
        styles = [s for s in styles if isinstance(s, str) and s.strip()]
        if not styles:
            barbers.sort(key=self.rating_score, reverse=True)
            return barbers

        if use_ai_analysis and self.generate_text:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(self.analyze_barber_reviews, b.get("name", ""), b.get("reviews", []), styles): b
                    for b in barbers
                    if b.get("reviews")
                }
                for future in as_completed(futures):
                    barber = futures[future]
                    try:
                        barber["style_analysis"] = future.result(timeout=5)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Review analysis failed for %s: %s", barber.get("name"), exc)
                        barber["style_analysis"] = {}

        for barber in barbers:
            relevance = self.calculate_style_relevance(barber, styles, barber.get("style_analysis", {}))
            barber["style_relevance_score"] = relevance
            barber["composite_score"] = (relevance * 0.7) + (self.rating_score(barber) / 5.0 * 0.3)

        barbers.sort(key=lambda b: b.get("composite_score", 0), reverse=True)
        return barbers

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()
