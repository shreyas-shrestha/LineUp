"""Haircut vocabulary for the Replicate change-haircut model and a keyword
fallback used when Gemini is unavailable."""

from __future__ import annotations

from typing import Optional

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
    "Double Dutch Braids", "French Fishtail Braid", "Waterfall Braid", "Rope Braid",
    "Heart Braid", "Halo Braid", "Crown Braid", "Braided Crown", "Bubble Braid",
    "Bubble Ponytail", "Ballerina Braids", "Milkmaid Braids", "Bohemian Braids",
    "Flat Twist", "Crown Twist", "Twisted Bun", "Twisted Half-Updo", "Twist and Pin Updo",
    "Chignon", "Simple Chignon", "Messy Chignon", "French Twist", "French Twist Updo",
    "French Roll", "Updo", "Messy Updo", "Knotted Updo", "Ballerina Bun",
    "Banana Clip Updo", "Beehive", "Bouffant", "Hair Bow", "Half-Up Top Knot",
    "Half-Up, Half-Down", "Messy Bun with a Headband", "Messy Bun with a Scarf",
    "Messy Fishtail Braid", "Sideswept Pixie", "Mohawk Fade", "Zig-Zag Part", "Victory Rolls",
]

# Longest keys are matched first so "side-swept bangs" wins over "bangs".
STYLE_KEYWORDS = {
    "long layers with bangs": "Layered",
    "layered with bangs": "Layered",
    "layers with bangs": "Layered",
    "side part with volume": "Side-Parted",
    "side-swept bangs": "Side-Swept Bangs",
    "blunt bangs": "Blunt Bangs",
    "modern fade": "Mohawk Fade",
    "taper fade": "Mohawk Fade",
    "classic fade": "Mohawk Fade",
    "buzz cut": "Crew Cut",
    "crew cut": "Crew Cut",
    "slick back": "Slicked Back",
    "slicked back": "Slicked Back",
    "side part": "Side-Parted",
    "side-part": "Side-Parted",
    "center part": "Center-Parted",
    "center-part": "Center-Parted",
    "soft waves": "Soft Waves",
    "messy bun": "Messy Bun",
    "pixie cut": "Pixie Cut",
    "a-line bob": "A-Line Bob",
    "long hair": "Half-Up, Half-Down",
    "long layers": "Layered",
    "side swept": "Side-Swept Bangs",
    "fade with": "Mohawk Fade",
    "top knot": "Top Knot",
    "fade": "Mohawk Fade",
    "buzz": "Crew Cut",
    "crewcut": "Crew Cut",
    "short": "Crew Cut",
    "quiff": "Slicked Back",
    "pompadour": "Slicked Back",
    "slickback": "Slicked Back",
    "sidepart": "Side-Parted",
    "sideparted": "Side-Parted",
    "parted": "Side-Parted",
    "undercut": "Undercut",
    "mohawk": "Mohawk",
    "curly": "Curly",
    "textured": "Tousled",
    "messy": "Tousled",
    "tousled": "Tousled",
    "afro": "Curly",
    "wavy": "Wavy",
    "waves": "Wavy",
    "straight": "Straight",
    "straightened": "Straightened",
    "bob": "Bob",
    "lob": "Lob",
    "pixie": "Pixie Cut",
    "bowl": "Pixie Cut",
    "bun": "Top Knot",
    "layered": "Layered",
    "layers": "Layered",
    "bangs": "Blunt Bangs",
    "dreadlocks": "Dreadlocks",
    "dreads": "Dreadlocks",
    "centerpart": "Center-Parted",
    "long": "Half-Up, Half-Down",
}

_SORTED_KEYS = sorted(STYLE_KEYWORDS, key=len, reverse=True)


def keyword_match(description: str) -> Optional[str]:
    lowered = description.lower().strip()
    for key in _SORTED_KEYS:
        if key in lowered:
            return STYLE_KEYWORDS[key]
    return None
