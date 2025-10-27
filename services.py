# services.py - Business Logic Services
import logging
import uuid
import json
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from PIL import Image
from io import BytesIO

from config import Config
from errors import ExternalAPIError, ValidationError, NotFoundError
from models import (
    DBSocialPost, DBAppointment, DBPortfolioItem, 
    DBSubscriptionPackage, DBClientSubscription,
    SessionLocal, to_dict
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATABASE SERVICE
# ============================================================================

class DatabaseService:
    """Service for database operations"""
    
    @staticmethod
    def get_session():
        """Get database session"""
        return SessionLocal()
    
    @staticmethod
    def save(obj):
        """Save object to database"""
        db = SessionLocal()
        try:
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return to_dict(obj)
        except Exception as e:
            db.rollback()
            logger.error(f"Database save error: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_all(model_class):
        """Get all records of a model"""
        db = SessionLocal()
        try:
            results = db.query(model_class).all()
            return [to_dict(r) for r in results]
        finally:
            db.close()
    
    @staticmethod
    def get_by_id(model_class, record_id):
        """Get record by ID"""
        db = SessionLocal()
        try:
            result = db.query(model_class).filter(model_class.id == record_id).first()
            return to_dict(result) if result else None
        finally:
            db.close()
    
    @staticmethod
    def update(model_class, record_id, updates):
        """Update record"""
        db = SessionLocal()
        try:
            record = db.query(model_class).filter(model_class.id == record_id).first()
            if not record:
                raise NotFoundError(f"{model_class.__name__} not found")
            for key, value in updates.items():
                setattr(record, key, value)
            db.commit()
            db.refresh(record)
            return to_dict(record)
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    @staticmethod
    def delete(model_class, record_id):
        """Delete record"""
        db = SessionLocal()
        try:
            record = db.query(model_class).filter(model_class.id == record_id).first()
            if record:
                db.delete(record)
                db.commit()
                return True
            return False
        finally:
            db.close()


# ============================================================================
# CACHE SERVICE (Memory-based, falls back from Redis)
# ============================================================================

class CacheService:
    """Simple in-memory cache with Redis fallback"""
    
    _cache = {}
    _redis_client = None
    
    @classmethod
    def initialize(cls):
        """Initialize Redis if available"""
        if Config.REDIS_URL:
            try:
                import redis
                cls._redis_client = redis.from_url(Config.REDIS_URL)
                cls._redis_client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis unavailable, using memory cache: {e}")
                cls._redis_client = None
    
    @classmethod
    def get(cls, key: str) -> Optional[dict]:
        """Get value from cache"""
        if cls._redis_client:
            try:
                value = cls._redis_client.get(key)
                return json.loads(value) if value else None
            except:
                pass
        
        # Memory fallback
        if key in cls._cache:
            data, expiry = cls._cache[key]
            if expiry > datetime.now():
                return data
            del cls._cache[key]
        return None
    
    @classmethod
    def set(cls, key: str, value: dict, ttl: int = 3600):
        """Set value in cache"""
        if cls._redis_client:
            try:
                cls._redis_client.setex(key, ttl, json.dumps(value))
                return
            except:
                pass
        
        # Memory fallback
        expiry = datetime.now() + timedelta(seconds=ttl)
        cls._cache[key] = (value, expiry)
    
    @classmethod
    def delete(cls, key: str):
        """Delete from cache"""
        if cls._redis_client:
            try:
                cls._redis_client.delete(key)
            except:
                pass
        cls._cache.pop(key, None)


# ============================================================================
# SOCIAL FEED SERVICE
# ============================================================================

class SocialService:
    """Service for social media operations"""
    
    @staticmethod
    def get_posts(limit: int = 50) -> List[dict]:
        """Get all social posts"""
        posts = DatabaseService.get_all(DBSocialPost)
        # Sort by timestamp descending
        posts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return posts[:limit]
    
    @staticmethod
    def create_post(username: str, avatar: str, image: str, caption: str) -> dict:
        """Create new social post"""
        post = DBSocialPost(
            id=str(uuid.uuid4()),
            username=username,
            avatar=avatar,
            image=image,
            caption=caption,
            likes=0,
            liked=False,
            timestamp=datetime.utcnow()
        )
        return DatabaseService.save(post)
    
    @staticmethod
    def toggle_like(post_id: str) -> dict:
        """Toggle like on a post"""
        db = SessionLocal()
        try:
            post = db.query(DBSocialPost).filter(DBSocialPost.id == post_id).first()
            if not post:
                raise NotFoundError("Post not found")
            
            post.liked = not post.liked
            post.likes += 1 if post.liked else -1
            db.commit()
            
            return {
                'success': True,
                'liked': post.liked,
                'likes': post.likes
            }
        finally:
            db.close()


# ============================================================================
# APPOINTMENT SERVICE
# ============================================================================

class AppointmentService:
    """Service for appointment operations"""
    
    @staticmethod
    def get_appointments(client_id: Optional[str] = None, barber_id: Optional[str] = None) -> List[dict]:
        """Get appointments filtered by client or barber"""
        db = SessionLocal()
        try:
            query = db.query(DBAppointment)
            if client_id:
                query = query.filter(DBAppointment.client_id == client_id)
            if barber_id:
                query = query.filter(DBAppointment.barber_id == barber_id)
            
            results = query.order_by(DBAppointment.date.desc()).all()
            return [to_dict(r) for r in results]
        finally:
            db.close()
    
    @staticmethod
    def create_appointment(data: dict) -> dict:
        """Create new appointment"""
        appointment = DBAppointment(
            id=str(uuid.uuid4()),
            client_name=data['client_name'],
            client_id=data.get('client_id', 'current-user'),
            barber_name=data['barber_name'],
            barber_id=data['barber_id'],
            date=data['date'],
            time=data['time'],
            service=data['service'],
            price=data.get('price', '$0'),
            status='pending',
            notes=data.get('notes', 'No special requests'),
            timestamp=datetime.utcnow()
        )
        return DatabaseService.save(appointment)
    
    @staticmethod
    def update_status(appointment_id: str, status: str) -> dict:
        """Update appointment status"""
        return DatabaseService.update(DBAppointment, appointment_id, {'status': status})


# ============================================================================
# PORTFOLIO SERVICE
# ============================================================================

class PortfolioService:
    """Service for barber portfolio operations"""
    
    @staticmethod
    def get_portfolio(barber_id: Optional[str] = None) -> List[dict]:
        """Get portfolio items"""
        db = SessionLocal()
        try:
            query = db.query(DBPortfolioItem)
            if barber_id:
                query = query.filter(DBPortfolioItem.barber_id == barber_id)
            
            results = query.order_by(DBPortfolioItem.timestamp.desc()).all()
            return [to_dict(r) for r in results]
        finally:
            db.close()
    
    @staticmethod
    def add_item(barber_id: str, style_name: str, image: str, description: str) -> dict:
        """Add portfolio item"""
        item = DBPortfolioItem(
            id=str(uuid.uuid4()),
            barber_id=barber_id,
            style_name=style_name,
            image=image,
            description=description,
            likes=0,
            date=datetime.now().strftime("%Y-%m-%d"),
            timestamp=datetime.utcnow()
        )
        return DatabaseService.save(item)


# ============================================================================
# GEMINI AI SERVICE
# ============================================================================

class GeminiService:
    """Service for Gemini AI integration"""
    
    @staticmethod
    def analyze_face(base64_image: str) -> dict:
        """Analyze face and recommend hairstyles"""
        if not Config.GEMINI_API_KEY:
            logger.warning("Gemini API not configured, using mock data")
            return GeminiService._get_mock_analysis()
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Decode and prepare image
            image_bytes = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_bytes))
            
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
            
            response = model.generate_content([prompt, image])
            response_text = response.text.strip()
            
            # Clean response
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.rfind("```")
                if end > start:
                    response_text = response_text[start:end].strip()
            
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return GeminiService._get_mock_analysis()
    
    @staticmethod
    def _get_mock_analysis() -> dict:
        """Return mock analysis data"""
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
                    "description": "Bold contrast with shaved sides",
                    "reason": "Adds edge and modern appeal"
                }
            ]
        }


# ============================================================================
# PLACES API SERVICE
# ============================================================================

class PlacesService:
    """Service for Google Places API"""
    
    @staticmethod
    def find_barbers(location: str, styles: List[str] = None) -> dict:
        """Find barbershops near location"""
        cache_key = f"barbers:{location.lower()}"
        
        # Check cache first
        cached = CacheService.get(cache_key)
        if cached:
            logger.info(f"Returning cached barbers for {location}")
            return {'barbers': cached, 'cached': True}
        
        if not Config.GOOGLE_PLACES_API_KEY:
            logger.warning("Google Places API not configured, using mock data")
            return PlacesService._get_mock_barbers(location)
        
        try:
            # Geocode location
            geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
            geocode_response = requests.get(geocode_url, params={
                'address': location,
                'key': Config.GOOGLE_PLACES_API_KEY
            }, timeout=10)
            
            geocode_data = geocode_response.json()
            if geocode_data['status'] != 'OK':
                raise ExternalAPIError('Google Geocoding', f"Location not found: {location}")
            
            lat = geocode_data['results'][0]['geometry']['location']['lat']
            lng = geocode_data['results'][0]['geometry']['location']['lng']
            
            # Search for barbershops
            places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            places_response = requests.get(places_url, params={
                'location': f"{lat},{lng}",
                'radius': 10000,
                'type': 'hair_care',
                'keyword': 'barber barbershop mens haircut',
                'key': Config.GOOGLE_PLACES_API_KEY
            }, timeout=10)
            
            places_data = places_response.json()
            if places_data['status'] != 'OK':
                raise ExternalAPIError('Google Places', f"Places API error: {places_data['status']}")
            
            barbers = PlacesService._process_places(places_data['results'][:10], styles or [])
            
            # Cache results
            CacheService.set(cache_key, barbers, Config.CACHE_DURATION)
            
            return {'barbers': barbers, 'real_data': True}
            
        except Exception as e:
            logger.error(f"Places API error: {e}")
            return PlacesService._get_mock_barbers(location)
    
    @staticmethod
    def _process_places(places: list, styles: list) -> list:
        """Process raw Places API data"""
        barbers = []
        for place in places:
            barbers.append({
                'id': place['place_id'],
                'name': place['name'],
                'address': place.get('vicinity', 'Address not available'),
                'rating': place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'avgCost': 25 + (place.get('price_level', 2) * 15),
                'specialties': PlacesService._extract_specialties(place['name'], styles),
                'location': place['geometry']['location'],
                'photo': None  # Could fetch photos with additional API call
            })
        return barbers
    
    @staticmethod
    def _extract_specialties(name: str, styles: list) -> list:
        """Extract specialties from barber name"""
        name_lower = name.lower()
        specialties = []
        
        if 'fade' in name_lower:
            specialties.append('Fade Specialist')
        if 'classic' in name_lower or 'traditional' in name_lower:
            specialties.append('Classic Cuts')
        if 'modern' in name_lower or 'style' in name_lower:
            specialties.append('Modern Styles')
        
        if not specialties:
            specialties = ['Haircut', 'Styling', 'Beard Trim']
        
        return specialties[:3]
    
    @staticmethod
    def _get_mock_barbers(location: str) -> dict:
        """Return mock barber data"""
        city = location.split(',')[0]
        return {
            'barbers': [
                {
                    'id': 'barber_1',
                    'name': f'Elite Cuts {city}',
                    'specialties': ['Fade', 'Taper', 'Modern Cuts'],
                    'rating': 4.9,
                    'avgCost': 45,
                    'address': f'Downtown {city}',
                    'phone': '(555) 123-4567'
                },
                {
                    'id': 'barber_2',
                    'name': f'The {city} Barber',
                    'specialties': ['Pompadour', 'Buzz Cut', 'Beard Trim'],
                    'rating': 4.8,
                    'avgCost': 55,
                    'address': f'Uptown {city}',
                    'phone': '(555) 123-4568'
                }
            ],
            'mock': True
        }


# Initialize cache on import
CacheService.initialize()

