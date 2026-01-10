"""Barber discovery and management endpoints."""

import logging
import os
import time
import uuid
from datetime import datetime

from flask import Blueprint, request

from lineup_backend.utils import cors_response, handle_options, api_response, safe_get_json
from lineup_backend import storage as memory_store

logger = logging.getLogger(__name__)

barbers_bp = Blueprint('barbers', __name__)

# Cache for Places API results
places_api_cache = {}
CACHE_DURATION = 3600  # 1 hour


def get_mock_barbers_for_location(location: str) -> list:
    """Generate mock barber data for a location."""
    city = location.split(',')[0] if ',' in location else location
    return [
        {
            "id": "barber_1",
            "name": f"Elite Cuts {city}",
            "specialties": ["Fade", "Taper", "Modern Cuts"],
            "rating": 4.9,
            "user_ratings_total": 127,
            "avgCost": 45,
            "address": f"Downtown {city}",
            "photo": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=400&h=300&fit=crop",
            "phone": "(555) 123-4567",
            "website": "https://elitecuts.example.com",
            "bookingUrl": "https://calendly.com/elitecuts/booking",
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={city}+barbershop",
            "hours": "Mon-Sat 9AM-8PM"
        },
        {
            "id": "barber_2",
            "name": f"The {city} Barber",
            "specialties": ["Pompadour", "Buzz Cut", "Beard Trim"],
            "rating": 4.8,
            "user_ratings_total": 89,
            "avgCost": 55,
            "address": f"Uptown {city}",
            "photo": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=400&h=300&fit=crop",
            "phone": "(555) 123-4568",
            "website": "",
            "bookingUrl": "https://booksy.com/thebarber",
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={city}+barbershop",
            "hours": "Tue-Sun 10AM-7PM"
        },
        {
            "id": "barber_3",
            "name": f"{city} Style Studio",
            "specialties": ["Modern Fade", "Beard Trim", "Styling"],
            "rating": 4.9,
            "user_ratings_total": 156,
            "avgCost": 65,
            "address": f"Midtown {city}",
            "photo": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=400&h=300&fit=crop",
            "phone": "(555) 123-4569",
            "website": "https://stylestudio.example.com",
            "bookingUrl": "https://squareup.com/appointments/book/stylestudio",
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={city}+barbershop",
            "hours": "Mon-Fri 8AM-6PM"
        }
    ]


@barbers_bp.route('/barbers', methods=['GET', 'OPTIONS'])
@handle_options("GET, OPTIONS")
def get_barbers():
    """Get nearby barbers using Google Places API or mock data."""
    location = request.args.get('location', 'Atlanta, GA')
    recommended_styles = request.args.get('styles', '').split(',')
    
    # Check cache
    cache_key = location.lower().strip()
    current_time = time.time()
    
    if cache_key in places_api_cache:
        cached = places_api_cache[cache_key]
        if current_time - cached['timestamp'] < CACHE_DURATION:
            logger.info(f"Returning cached barber data for {location}")
            return cors_response({
                "barbers": cached['data'],
                "location": location,
                "cached": True
            })
    
    # Check for Google Places API key
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    
    if not api_key:
        logger.warning("Google Places API key not configured, using mock data")
        return cors_response({
            "barbers": get_mock_barbers_for_location(location),
            "location": location,
            "mock": True,
            "reason": "API key not configured"
        })
    
    try:
        import requests
        
        # Geocode the location
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geocode_response = requests.get(geocode_url, params={
            'address': location,
            'key': api_key
        }, timeout=10)
        geocode_data = geocode_response.json()
        
        if geocode_data['status'] != 'OK' or not geocode_data.get('results'):
            raise Exception(f"Location not found: {location}")
        
        lat = geocode_data['results'][0]['geometry']['location']['lat']
        lng = geocode_data['results'][0]['geometry']['location']['lng']
        
        # Search for barbershops
        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_response = requests.get(places_url, params={
            'location': f"{lat},{lng}",
            'radius': 10000,
            'type': 'hair_care',
            'keyword': 'barber barbershop mens haircut',
            'key': api_key
        }, timeout=10)
        places_data = places_response.json()
        
        if places_data['status'] != 'OK':
            raise Exception(f"Places API error: {places_data.get('status')}")
        
        # Process results
        barbers = []
        for place in places_data['results'][:15]:
            # Get place details
            details = {}
            try:
                details_response = requests.get(
                    "https://maps.googleapis.com/maps/api/place/details/json",
                    params={
                        'place_id': place['place_id'],
                        'fields': 'name,formatted_address,formatted_phone_number,opening_hours,website,rating,user_ratings_total,photos,reviews',
                        'key': api_key
                    },
                    timeout=10
                )
                details_data = details_response.json()
                if details_data['status'] == 'OK':
                    details = details_data.get('result', {})
            except Exception:
                pass
            
            # Build barber info
            photo_url = None
            if 'photos' in place and place['photos']:
                photo_ref = place['photos'][0].get('photo_reference')
                if photo_ref:
                    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={api_key}"
            
            place_lat = place['geometry']['location']['lat']
            place_lng = place['geometry']['location']['lng']
            
            barber_info = {
                'id': place['place_id'],
                'name': place['name'],
                'address': details.get('formatted_address', place.get('vicinity', 'Address not available')),
                'rating': place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'avgCost': 25 + (place.get('price_level', 2) * 15),
                'phone': details.get('formatted_phone_number', 'Call for info'),
                'website': details.get('website', ''),
                'bookingUrl': details.get('website', ''),
                'google_maps_url': f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}",
                'hours': details.get('opening_hours', {}).get('weekday_text', []),
                'open_now': place.get('opening_hours', {}).get('open_now'),
                'photo': photo_url,
                'specialties': ['Haircut', 'Styling', 'Beard Trim'],
                'place_id': place['place_id']
            }
            
            barbers.append(barber_info)
        
        # Sort by rating
        barbers.sort(key=lambda x: (x['rating'] * min(x['user_ratings_total'], 100) / 100), reverse=True)
        
        # Cache results
        places_api_cache[cache_key] = {
            'data': barbers[:10],
            'timestamp': current_time
        }
        
        logger.info(f"Found {len(barbers)} barbershops in {location}")
        
        return cors_response({
            "barbers": barbers[:10],
            "location": location,
            "real_data": True,
            "total_found": len(barbers)
        })
        
    except Exception as e:
        logger.error(f"Error fetching barber data: {str(e)}")
        return cors_response({
            "barbers": get_mock_barbers_for_location(location),
            "location": location,
            "mock": True,
            "error": str(e)
        })


@barbers_bp.route('/barbers/<barber_id>/reviews', methods=['GET', 'POST', 'OPTIONS'])
@handle_options("GET, POST, OPTIONS")
def handle_reviews(barber_id):
    """Get or add reviews for a barber."""
    
    if request.method == 'GET':
        # Check if it's a Google place_id
        api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
        is_google_place_id = len(barber_id) >= 20 and barber_id[0].isalpha()
        
        if api_key and is_google_place_id:
            try:
                import requests
                
                details_response = requests.get(
                    "https://maps.googleapis.com/maps/api/place/details/json",
                    params={
                        'place_id': barber_id,
                        'fields': 'name,rating,user_ratings_total,reviews',
                        'key': api_key
                    },
                    timeout=10
                )
                details_data = details_response.json()
                
                if details_data.get('status') == 'OK' and 'result' in details_data:
                    result = details_data['result']
                    reviews = result.get('reviews', [])
                    
                    google_reviews = []
                    for review in reviews[:10]:
                        review_date = 'Recent'
                        if review.get('time'):
                            try:
                                review_date = datetime.fromtimestamp(review['time']).strftime('%Y-%m-%d')
                            except Exception:
                                pass
                        
                        google_reviews.append({
                            'id': f"{review.get('author_name', '')}_{review.get('time', 0)}",
                            'username': review.get('author_name', 'Anonymous'),
                            'rating': review.get('rating', 5),
                            'text': review.get('text', ''),
                            'date': review_date,
                            'profile_photo': review.get('profile_photo_url', ''),
                            'relative_time': review.get('relative_time_description', '')
                        })
                    
                    return cors_response({
                        'reviews': google_reviews,
                        'average_rating': result.get('rating', 0),
                        'total_reviews': result.get('user_ratings_total', 0),
                        'source': 'google'
                    })
            except Exception as e:
                logger.error(f"Error fetching Google Reviews: {str(e)}")
        
        # Fallback to mock reviews
        reviews = memory_store.barber_reviews.get(barber_id, [])
        avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews) if reviews else 0
        
        return cors_response({
            'reviews': reviews,
            'average_rating': avg_rating,
            'total_reviews': len(reviews),
            'source': 'mock'
        })
    
    elif request.method == 'POST':
        try:
            data = safe_get_json()
            
            new_review = {
                "id": str(uuid.uuid4()),
                "username": data.get("username", "anonymous"),
                "rating": data.get("rating", 5),
                "text": data.get("text", ""),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.now().isoformat()
            }
            
            if barber_id not in memory_store.barber_reviews:
                memory_store.barber_reviews[barber_id] = []
            memory_store.barber_reviews[barber_id].append(new_review)
            
            return api_response(data={"review": new_review}, message="Review added", status=201)
            
        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            return api_response(error="Failed to create review", status=400)


@barbers_bp.route('/barbers/<barber_id>/availability', methods=['GET', 'PUT', 'OPTIONS'])
@handle_options("GET, PUT, OPTIONS")
def manage_availability(barber_id):
    """Get or update barber availability."""
    
    if request.method == 'GET':
        # Return default availability
        availability = {
            "barberId": barber_id,
            "workingHours": {
                "monday": {"enabled": True, "start": "09:00", "end": "18:00"},
                "tuesday": {"enabled": True, "start": "09:00", "end": "18:00"},
                "wednesday": {"enabled": True, "start": "09:00", "end": "18:00"},
                "thursday": {"enabled": True, "start": "09:00", "end": "18:00"},
                "friday": {"enabled": True, "start": "09:00", "end": "18:00"},
                "saturday": {"enabled": True, "start": "09:00", "end": "17:00"},
                "sunday": {"enabled": False, "start": "09:00", "end": "17:00"}
            },
            "breakTimes": [],
            "blockedDates": [],
            "serviceDuration": 30,
            "bufferTime": 15,
            "timezone": "America/New_York"
        }
        return cors_response({"availability": availability})
    
    elif request.method == 'PUT':
        try:
            data = safe_get_json()
            
            availability_data = {
                "barberId": barber_id,
                "workingHours": data.get("workingHours", {}),
                "breakTimes": data.get("breakTimes", []),
                "blockedDates": data.get("blockedDates", []),
                "serviceDuration": data.get("serviceDuration", 30),
                "bufferTime": data.get("bufferTime", 15),
                "timezone": data.get("timezone", "America/New_York"),
                "updatedAt": datetime.now().isoformat()
            }
            
            return cors_response({"success": True, "availability": availability_data})
            
        except Exception as e:
            logger.error(f"Error updating availability: {str(e)}")
            return api_response(error="Failed to update availability", status=400)


@barbers_bp.route('/barbers/<barber_id>/services', methods=['GET', 'POST', 'OPTIONS'])
@handle_options("GET, POST, OPTIONS")
def manage_services(barber_id):
    """Get or add services for a barber."""
    
    if request.method == 'GET':
        # Return default services
        services = [
            {"id": "1", "name": "Haircut", "price": 30, "duration": 30, "category": "Hair"},
            {"id": "2", "name": "Beard Trim", "price": 15, "duration": 15, "category": "Beard"},
            {"id": "3", "name": "Haircut + Beard", "price": 40, "duration": 45, "category": "Package"}
        ]
        return cors_response({"services": services})
    
    elif request.method == 'POST':
        try:
            data = safe_get_json()
            
            new_service = {
                "id": str(uuid.uuid4()),
                "barberId": barber_id,
                "name": data.get("name", ""),
                "price": data.get("price", 0),
                "duration": data.get("duration", 30),
                "category": data.get("category", "General"),
                "description": data.get("description", ""),
                "createdAt": datetime.now().isoformat()
            }
            
            return api_response(data={"service": new_service}, message="Service added", status=201)
            
        except Exception as e:
            logger.error(f"Error creating service: {str(e)}")
            return api_response(error="Failed to create service", status=400)


@barbers_bp.route('/barbers/<barber_id>/clients', methods=['GET', 'OPTIONS'])
@handle_options("GET, OPTIONS")
def get_clients(barber_id):
    """Get clients for a barber based on appointments."""
    try:
        appointments_list = [apt for apt in memory_store.appointments if apt.get('barberId') == barber_id]
        
        # Group by client
        clients_dict = {}
        for apt in appointments_list:
            client_id = apt.get('clientId')
            if not client_id:
                continue
            
            if client_id not in clients_dict:
                clients_dict[client_id] = {
                    "clientId": client_id,
                    "clientName": apt.get('clientName', 'Unknown'),
                    "totalVisits": 0,
                    "lastVisit": None,
                    "totalSpent": 0,
                    "appointments": []
                }
            
            clients_dict[client_id]["totalVisits"] += 1
            clients_dict[client_id]["appointments"].append(apt)
            
            # Calculate total spent
            price_str = apt.get('price', '$0').replace('$', '').replace(',', '')
            try:
                clients_dict[client_id]["totalSpent"] += float(price_str)
            except ValueError:
                pass
        
        clients = list(clients_dict.values())
        clients.sort(key=lambda x: x.get('totalVisits', 0), reverse=True)
        
        return cors_response({"clients": clients})
        
    except Exception as e:
        logger.error(f"Error getting clients: {str(e)}")
        return api_response(error="Failed to get clients", status=400)

