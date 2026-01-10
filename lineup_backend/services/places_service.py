"""Google Places API service for barber discovery."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import CachedService

logger = logging.getLogger(__name__)


class PlacesService(CachedService):
    """Service for Google Places API operations."""

    DAILY_LIMIT = 100  # Free tier limit
    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    PHOTO_URL = "https://maps.googleapis.com/maps/api/place/photo"

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(cache_duration=3600, max_cache_size=50)
        self._api_key = api_key
        self._requests = None
        
        if api_key:
            try:
                import requests
                self._requests = requests
                logger.info("Places API configured successfully")
            except ImportError:
                logger.error("requests library not available")

    def is_configured(self) -> bool:
        """Check if Places API is properly configured."""
        return bool(self._api_key and self._requests)

    def health_check(self) -> Dict[str, Any]:
        """Return health information about Places service."""
        return {
            "configured": self.is_configured(),
            "daily_usage": self._get_usage(),
            "daily_limit": self.DAILY_LIMIT,
            "remaining": max(0, self.DAILY_LIMIT - self._get_usage()),
            "cache": self.get_cache_stats(),
        }

    def can_make_call(self) -> bool:
        """Check if we can make a Places API call."""
        return self.is_configured() and self._can_make_call(limit=self.DAILY_LIMIT)

    def search_barbers(
        self,
        location: str,
        recommended_styles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search for barbershops near a location.
        
        Args:
            location: City, address, or ZIP code
            recommended_styles: Optional list of recommended styles for matching
            
        Returns:
            Dictionary with barbers list and metadata
        """
        # Check cache first
        cache_key = location.lower().strip()
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Returning cached barber data for {location}")
            return {
                "barbers": cached,
                "location": location,
                "cached": True,
            }

        if not self.can_make_call():
            logger.warning("Places API limit reached or not configured")
            return {
                "barbers": self._get_mock_barbers(location),
                "location": location,
                "mock": True,
                "reason": "API limit reached" if self.is_configured() else "API not configured",
            }

        try:
            # Geocode the location
            coords = self._geocode(location)
            if not coords:
                return {
                    "barbers": self._get_mock_barbers(location),
                    "location": location,
                    "mock": True,
                    "reason": "Location not found",
                }

            lat, lng = coords

            # Search for barbershops
            self._increment_usage()
            response = self._requests.get(
                self.PLACES_URL,
                params={
                    "location": f"{lat},{lng}",
                    "radius": 10000,  # 10km
                    "type": "hair_care",
                    "keyword": "barber barbershop mens haircut",
                    "key": self._api_key,
                },
                timeout=10,
            )
            data = response.json()

            if data.get("status") != "OK":
                raise Exception(f"Places API error: {data.get('status')}")

            # Process results
            barbers = []
            for place in data.get("results", [])[:15]:
                barber_info = self._process_place(place, recommended_styles or [])
                if barber_info:
                    barbers.append(barber_info)

            # Sort by rating
            barbers.sort(
                key=lambda x: x["rating"] * (min(x["user_ratings_total"], 100) / 100),
                reverse=True,
            )

            # Cache top 10
            top_barbers = barbers[:10]
            self._set_cache(cache_key, top_barbers)

            logger.info(f"Found {len(barbers)} barbershops in {location}")
            return {
                "barbers": top_barbers,
                "location": location,
                "real_data": True,
                "total_found": len(barbers),
            }

        except Exception as e:
            logger.error(f"Error fetching barber data: {e}")
            return {
                "barbers": self._get_mock_barbers(location),
                "location": location,
                "mock": True,
                "error": str(e),
            }

    def get_place_reviews(self, place_id: str) -> Dict[str, Any]:
        """Get reviews for a specific place.
        
        Args:
            place_id: Google Place ID
            
        Returns:
            Dictionary with reviews and stats
        """
        if not self.can_make_call():
            return {"reviews": [], "source": "unavailable"}

        try:
            self._increment_usage()
            response = self._requests.get(
                self.DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "name,rating,user_ratings_total,reviews",
                    "key": self._api_key,
                },
                timeout=10,
            )
            data = response.json()

            if data.get("status") != "OK":
                return {"reviews": [], "source": "error"}

            result = data.get("result", {})
            reviews = []
            
            for review in result.get("reviews", [])[:10]:
                try:
                    review_date = "Recent"
                    if review.get("time"):
                        review_date = datetime.fromtimestamp(review["time"]).strftime("%Y-%m-%d")
                    
                    reviews.append({
                        "id": f"{review.get('author_name', '')}_{review.get('time', 0)}",
                        "username": review.get("author_name", "Anonymous"),
                        "rating": review.get("rating", 5),
                        "text": review.get("text", ""),
                        "date": review_date,
                        "profile_photo": review.get("profile_photo_url", ""),
                        "relative_time": review.get("relative_time_description", ""),
                    })
                except Exception as e:
                    logger.error(f"Error processing review: {e}")

            return {
                "reviews": reviews,
                "average_rating": result.get("rating", 0),
                "total_reviews": result.get("user_ratings_total", 0),
                "source": "google",
            }

        except Exception as e:
            logger.error(f"Error fetching reviews: {e}")
            return {"reviews": [], "source": "error", "error": str(e)}

    def _geocode(self, location: str) -> Optional[tuple]:
        """Geocode a location string to coordinates."""
        try:
            response = self._requests.get(
                self.GEOCODE_URL,
                params={"address": location, "key": self._api_key},
                timeout=10,
            )
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                loc = data["results"][0]["geometry"]["location"]
                return (loc["lat"], loc["lng"])
            return None
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return None

    def _process_place(
        self,
        place: Dict[str, Any],
        recommended_styles: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Process a place result into barber info."""
        try:
            # Get details
            details = self._get_place_details(place["place_id"])

            # Determine specialties
            specialties = self._determine_specialties(place["name"], recommended_styles)

            # Get photo URL
            photo_url = None
            if place.get("photos"):
                photo_ref = place["photos"][0].get("photo_reference")
                if photo_ref:
                    photo_url = f"{self.PHOTO_URL}?maxwidth=400&photoreference={photo_ref}&key={self._api_key}"

            lat = place["geometry"]["location"]["lat"]
            lng = place["geometry"]["location"]["lng"]

            return {
                "id": place["place_id"],
                "name": place["name"],
                "address": details.get("formatted_address", place.get("vicinity", "Address not available")),
                "rating": place.get("rating", 0),
                "user_ratings_total": place.get("user_ratings_total", 0),
                "price_level": place.get("price_level", 2),
                "avgCost": 25 + (place.get("price_level", 2) * 15),
                "phone": details.get("formatted_phone_number", "Call for info"),
                "website": details.get("website", ""),
                "bookingUrl": details.get("website", ""),
                "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
                "hours": details.get("opening_hours", {}).get("weekday_text", []),
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "photo": photo_url,
                "specialties": specialties,
                "location": {"lat": lat, "lng": lng},
                "place_id": place["place_id"],
            }
        except Exception as e:
            logger.error(f"Error processing place: {e}")
            return None

    def _get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed information about a place."""
        try:
            response = self._requests.get(
                self.DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "formatted_address,formatted_phone_number,opening_hours,website",
                    "key": self._api_key,
                },
                timeout=10,
            )
            data = response.json()
            return data.get("result", {}) if data.get("status") == "OK" else {}
        except Exception:
            return {}

    def _determine_specialties(
        self,
        name: str,
        recommended_styles: List[str],
    ) -> List[str]:
        """Determine barber specialties based on name and recommendations."""
        specialties = []
        name_lower = name.lower()

        if "fade" in name_lower:
            specialties.append("Fade Specialist")
        if "classic" in name_lower or "traditional" in name_lower:
            specialties.append("Classic Cuts")
        if "modern" in name_lower or "style" in name_lower:
            specialties.append("Modern Styles")
        if "beard" in name_lower:
            specialties.append("Beard Trim")

        for style in recommended_styles:
            if style and "fade" in style.lower():
                specialties.append("Fade Expert")
            elif style and "classic" in style.lower():
                specialties.append("Classic Styles")

        if not specialties:
            specialties = ["Haircut", "Styling", "Beard Trim"]

        return list(set(specialties))[:3]

    def _get_mock_barbers(self, location: str) -> List[Dict[str, Any]]:
        """Return mock barber data."""
        city = location.split(",")[0] if "," in location else location
        return [
            {
                "id": "mock_1",
                "name": f"Elite Cuts {city}",
                "specialties": ["Fade", "Taper", "Modern Cuts"],
                "rating": 4.9,
                "user_ratings_total": 127,
                "avgCost": 45,
                "address": f"Downtown {city}",
                "photo": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop",
                "phone": "(555) 123-4567",
                "website": "",
                "bookingUrl": "",
                "google_maps_url": "https://www.google.com/maps",
                "hours": "Mon-Sat 9AM-8PM",
            },
            {
                "id": "mock_2",
                "name": f"The {city} Barber",
                "specialties": ["Pompadour", "Buzz Cut", "Beard Trim"],
                "rating": 4.8,
                "user_ratings_total": 89,
                "avgCost": 55,
                "address": f"Uptown {city}",
                "photo": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop",
                "phone": "(555) 123-4568",
                "website": "",
                "bookingUrl": "",
                "google_maps_url": "https://www.google.com/maps",
                "hours": "Tue-Sun 10AM-7PM",
            },
            {
                "id": "mock_3",
                "name": f"{city} Style Studio",
                "specialties": ["Modern Fade", "Beard Trim", "Styling"],
                "rating": 4.7,
                "user_ratings_total": 156,
                "avgCost": 65,
                "address": f"Midtown {city}",
                "photo": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop",
                "phone": "(555) 123-4569",
                "website": "",
                "bookingUrl": "",
                "google_maps_url": "https://www.google.com/maps",
                "hours": "Mon-Fri 8AM-6PM",
            },
        ]
