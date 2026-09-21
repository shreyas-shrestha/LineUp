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

# Relevance thresholds for the badge on a card. Below "some" nothing is claimed.
# "strong" needs Gemini's read of the reviews (keywords alone cap at 0.5);
# "some" is reachable from reviews mentioning one recommended style.
MATCH_LEVELS = ((0.55, "strong"), (0.3, "good"), (0.08, "some"))


def _style_words(style: str) -> List[str]:
    return [w.lower() for w in str(style).split() if len(w) > 2]


def _plural(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


# Hair textures a barber's reviews talk about, and the words that mean them.
HAIR_WORDS = {
    "curly": ["curly", "curls", "curl"],
    "coily": ["coily", "coils", "kinky", "4c", "afro", "natural hair"],
    "wavy": ["wavy", "waves"],
    "straight": ["straight hair", "fine hair", "thin hair"],
    "thick": ["thick hair", "dense"],
}


def _hair_words(hair: Optional[str]) -> List[str]:
    key = str(hair or "").strip().lower()
    return HAIR_WORDS.get(key, [key] if key else [])


def describe_need(styles: List[str], hair: Optional[str]) -> str:
    """One line the results page leads with: what kind of barber this person needs."""
    cuts = [s for s in styles if s][:2]
    if not cuts and not hair:
        return ""
    text = "A barber who does " + (" or ".join(c.lower() for c in cuts) if cuts else "your recommended cuts")
    if hair:
        text += f" on {str(hair).lower()} hair"
    return text


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

    def build_search_keywords(self, recommended_styles: List[str], hair: Optional[str] = None) -> str:
        base_keywords = "barber barbershop mens haircut"
        if hair and str(hair).strip():
            base_keywords += f" {str(hair).strip().lower()} hair"
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

    def analyze_barber_reviews(self, barber_name: str, reviews: List[Dict[str, Any]], styles: List[str], hair: Optional[str] = None) -> Dict[str, Any]:
        empty = {"overall_match_score": 0.0, "matches": []}
        if not self.generate_text or not styles or not reviews:
            return empty

        cache_key = f"{barber_name}:{','.join(sorted(styles))}:{hair or ''}"
        cached = self._recall(cache_key)
        if cached is not None:
            return cached

        snippets = [r.get("text", "").strip()[:300] for r in reviews[:5] if r.get("text", "").strip()]
        if not snippets:
            return empty

        hair_line = f"CLIENT HAIR TEXTURE: {hair}\n" if hair else ""
        prompt = (
            "Analyze these barbershop reviews to determine expertise in specific haircut styles"
            + (" and with the client's hair texture" if hair else "")
            + ".\n\n"
            f"BARBERSHOP: {barber_name}\nSTYLES TO MATCH: {', '.join(styles)}\n{hair_line}"
            f"REVIEWS: {' | '.join(snippets)[:2000]}\n\n"
            "Return ONLY valid JSON (no markdown):\n"
            '{"overall_match_score": 0.0-1.0, "matches": [{"style": "style name", "confidence": 0.0-1.0, "evidence": "brief reason, quoting the review where possible"}]}\n'
            "Rules: overall_match_score 0.0 (no evidence) to 1.0 (strong evidence); a match may name the hair texture instead of a style; empty matches if none."
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
    def calculate_style_relevance(barber: Dict[str, Any], styles: List[str], style_analysis: Dict[str, Any], hair: Optional[str] = None) -> float:
        if not styles and not hair:
            return 0.0
        score = 0.0
        name_lower = barber.get("name", "").lower()
        styles = styles or []

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
                    keyword_match += 0.2 / max(1, len(styles))
            score += min(keyword_match, 0.2)
            # Reviews that talk about the client's hair texture are evidence
            # the shop knows how to cut it, which is half of "the right barber".
            if hair and any(w in reviews_text for w in _hair_words(hair)):
                score += 0.15
        return min(score, 1.0)

    @staticmethod
    def rating_score(barber: Dict[str, Any]) -> float:
        return float(barber.get("rating", 0) or 0) * min(int(barber.get("user_ratings_total", 0) or 0), 100) / 100

    @staticmethod
    def describe_match(
        barber: Dict[str, Any],
        styles: List[str],
        analysis: Dict[str, Any],
        relevance: float,
        hair: Optional[str] = None,
    ) -> Dict[str, Any]:
        """The ``match`` block a card renders: a level, the best style, and up
        to three plain reasons about what this person needs. Reasons come from
        evidence, strongest first: Gemini's read of the reviews, then the shop
        name, then reviews mentioning the cut, then reviews mentioning the
        hair texture. When a shop has no evidence for the need, the first
        reason says so rather than falling back to a generic rating line -
        the match is the product, so its absence is worth stating."""
        reasons: List[str] = []
        top_style: Optional[str] = None
        styles = styles or []

        matches = [m for m in (analysis or {}).get("matches", []) if isinstance(m, dict)]
        matches.sort(key=lambda m: -float(m.get("confidence") or 0))
        for m in matches[:2]:
            style, evidence = str(m.get("style") or "").strip(), str(m.get("evidence") or "").strip()
            if style and top_style is None:
                top_style = style
            if evidence:
                reasons.append(f"{style}: {evidence}" if style else evidence)

        name_lower = str(barber.get("name", "")).lower()
        for style in styles:
            hit = next((w for w in _style_words(style) if w in name_lower), None)
            if hit:
                reasons.append(f"The name says {hit}")
                top_style = top_style or style
                break

        reviews = [str(r.get("text") or "").lower() for r in barber.get("reviews", [])[:10]]
        for style in styles:
            words = _style_words(style)
            count = sum(1 for text in reviews if any(w in text for w in words))
            if count:
                verb = "mentions" if count == 1 else "mention"
                reasons.append(f"{_plural(count, 'review')} {verb} {style.lower()}")
                top_style = top_style or style
                break

        if hair:
            words = _hair_words(hair)
            count = sum(1 for text in reviews if any(w in text for w in words))
            if count:
                verb = "mentions" if count == 1 else "mention"
                reasons.append(f"{_plural(count, 'review')} {verb} {str(hair).lower()} hair")

        need_based = len(reasons)
        rating = float(barber.get("rating", 0) or 0)
        total = int(barber.get("user_ratings_total", 0) or 0)
        ranked_for_need = bool(styles or hair)
        if ranked_for_need and not need_based:
            what = (styles[0].lower() if styles else f"{str(hair).lower()} hair")
            reasons.append(f"No reviews mention {what} yet, so this one is ranked on its rating")
        if rating >= 4.5 and total >= 20:
            reasons.append(f"Rated {rating:.1f} by {total} people")

        level = next((name for floor, name in MATCH_LEVELS if relevance >= floor), None) if ranked_for_need else None
        deduped = list(dict.fromkeys(r for r in reasons if r))[:3]
        return {
            "score": round(relevance, 2) if ranked_for_need else None,
            "level": level,
            "top_style": top_style,
            "reasons": deduped,
            "evidence": need_based > 0,
        }

    def rank_barbers(
        self,
        barbers: List[Dict[str, Any]],
        styles: List[str],
        use_ai_analysis: bool = True,
        hair: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        styles = [s for s in styles if isinstance(s, str) and s.strip()]
        hair = str(hair).strip().lower() if hair else None
        if not styles and not hair:
            barbers.sort(key=self.rating_score, reverse=True)
            for barber in barbers:
                barber["match"] = self.describe_match(barber, [], {}, 0.0)
            return barbers

        if use_ai_analysis and self.generate_text and styles:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(self.analyze_barber_reviews, b.get("name", ""), b.get("reviews", []), styles, hair): b
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
            analysis = barber.get("style_analysis", {})
            relevance = self.calculate_style_relevance(barber, styles, analysis, hair)
            barber["style_relevance_score"] = relevance
            barber["composite_score"] = (relevance * 0.7) + (self.rating_score(barber) / 5.0 * 0.3)
            barber["match"] = self.describe_match(barber, styles, analysis, relevance, hair)

        barbers.sort(key=lambda b: b.get("composite_score", 0), reverse=True)
        return barbers

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()
