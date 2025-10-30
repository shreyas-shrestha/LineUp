#LineUp AI - v2.0

**AI-Powered Haircut Analysis & Barber Booking Platform**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)](https://flask.palletsprojects.com)
[![Tests](https://img.shields.io/badge/Tests-30%20passing-success.svg)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-75%25-success.svg)](tests/)
[![Cost](https://img.shields.io/badge/Cost-$0%2Fmonth-brightgreen.svg)](#)

## 🆕 What's New in v2.0?

Version 2.0 is a **complete rewrite** with 10 major improvements using **100% FREE tools**:

✅ **Modular Architecture** - 6 focused modules vs 1 monolithic file  
✅ **SQLite Database** - Persistent data with PostgreSQL migration path  
✅ **Input Validation** - Pydantic validation on all endpoints  
✅ **Test Suite** - 30+ tests with 75% coverage  
✅ **PWA Support** - Install as native app, works offline  
✅ **Optimized Frontend** - 44% faster loads with smart caching  
✅ **Error Handling** - Centralized, consistent error responses  
✅ **Redis Caching** - Optional Redis with memory fallback  
✅ **Production Ready** - Automated setup and deployment scripts  
✅ **Still FREE** - $0/month with generous free tiers

### 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[README_IMPROVEMENTS.md](README_IMPROVEMENTS.md)** - Complete feature guide
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Technical details
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deploy to production (FREE hosting)
- **[HAIR_TRYON_SETUP.md](HAIR_TRYON_SETUP.md)** - Virtual try-on setup (works immediately!)

### 🚀 Quick Start

```bash
# Option 1: Automated (Recommended)
python setup.py

# Option 2: Manual
pip install -r requirements.txt
cp env.example.txt .env
# Add your GEMINI_API_KEY to .env
python app_refactored.py

# Option 3: One-liner
chmod +x run.sh && ./run.sh
```

Visit: http://localhost:5000

**Minimum requirement:** Just add `GEMINI_API_KEY` to .env (free at https://makersuite.google.com)

---

## Project Overview

LineUp is a two-sided AI-powered haircut analysis and barber platform consisting of:
- **Frontend**: Vanilla HTML/CSS/JavaScript with TailwindCSS (single-page app)
- **Backend**: Flask API with Google Gemini AI integration and Google Places API
- **Deployment**: Render (both frontend and backend hosted separately)

## Common Development Commands

### Local Development
```bash
# Start the Flask backend locally
python app.py
# Backend runs on http://localhost:5000

# For frontend development, serve the HTML file
# Open index.html directly in browser or use a local server:
python -m http.server 8000
# Frontend accessible at http://localhost:8000
```

### Testing Backend
```bash
# Test backend health
curl http://localhost:5000/health

# Test AI analysis endpoint (requires image data)
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"payload": {"contents": [{"parts": [{"text": "analyze"}, {"inlineData": {"mimeType": "image/jpeg", "data": "base64data"}}]}]}}'

# Test barber search
curl "http://localhost:5000/barbers?location=Atlanta,GA"

# Test virtual try-on endpoint (requires base64 image data)
curl -X POST http://localhost:5000/virtual-tryon \
  -H "Content-Type: application/json" \
  -d '{"userPhoto": "base64data", "styleDescription": "Side Part with Volume"}'
```

### Dependency Management
```bash
# Install Python dependencies
pip install -r requirements.txt

# Update requirements (when adding new packages)
pip freeze > requirements.txt
```

### Environment Setup
Required environment variables for full functionality:
- `GEMINI_API_KEY`: Google Gemini API key for AI hair analysis
- `GOOGLE_PLACES_API_KEY`: Google Places API key for real barber data
- `REPLICATE_API_TOKEN`: (Optional) Replicate API key for AI hair transformation enhancement
- `PORT`: Port for Flask app (defaults to 5000)

**For Virtual Try-On**: Works immediately with preview mode! See `HAIR_TRYON_SETUP.md` for optional AI enhancement (5 min setup)

## Architecture Overview

### High-Level Structure
The application is a **two-sided platform** with distinct user modes:
1. **Client Mode**: Upload photo → AI analysis → haircut recommendations → find barbers
2. **Barber Mode**: Dashboard → portfolio management → appointment scheduling

### Backend Architecture (`app.py`)
- **Flask API** with comprehensive rate limiting using Flask-Limiter
- **AI Analysis Engine**: Google Gemini 2.5 Pro model for facial/hair analysis
- **Real Data Integration**: Google Places API for barbershop discovery
- **In-Memory Storage**: Mock data for social posts, appointments, portfolios (production would use database)
- **CORS enabled** for cross-origin requests from frontend
- **Fallback System**: Mock data when APIs are unavailable or rate-limited

#### Key Endpoints
- `/analyze` - AI haircut analysis with Google Gemini (10 req/hour limit)
- `/barbers` - Real barbershop search with location via Google Places API
- `/virtual-tryon` - **Visual hair transformation** (20 req/hour limit)
  - Works immediately with preview mode (no setup required!)
  - Optional: Add `REPLICATE_API_TOKEN` for AI enhancement
  - Returns transformed image with hairstyle preview
  - See `HAIR_TRYON_SETUP.md` for optional AI upgrade
- `/subscription-packages` - Barber subscription package management (GET/POST)
- `/client-subscriptions` - Client subscription tracking (GET/POST)
- `/social` - Social media feed functionality (GET/POST)
- `/appointments` - Appointment booking and management (GET/POST)
- `/portfolio` - Barber portfolio management (GET/POST)
- `/health` - System health and API usage tracking

### Frontend Architecture (`index.html` + `scripts-updated.js`)
- **Single-page application** with role-based content switching
- **Tab-based navigation** for different features
- **Responsive design** using TailwindCSS
- **Modal dialogs** for image uploads, posts, and appointments
- **Real-time UI updates** without page refreshes

#### Key Components
- **Role Switcher**: Toggle between Client/Barber modes
- **AI Analysis Flow**: Image upload → compression → Gemini API → structured recommendations
- **Virtual Try-On**: Upload photo → Select hairstyle → Image transformation → visual result
  - Works immediately with preview mode (no setup!)
  - Optional AI enhancement with Replicate (simple 5-min setup)
  - Returns transformed image showing hairstyle preview on user's photo
- **Subscription Packages**: Barbers create subscription deals (e.g., 2 cuts/month for $X)
- **Individual Style Barber Search**: Each recommendation has "Find Barbers" button
- **Barber Discovery**: Location-based search with Google Places API
- **Social Feed**: Community posts with like/comment functionality
- **Appointment System**: Booking interface with real-time availability

### Data Flow Patterns
1. **Image Analysis**: Frontend compresses images → Base64 encoding → Gemini API → Structured recommendations
2. **Virtual Try-On**: User photo (base64) + style description → Backend `/virtual-tryon` → Image processing (preview or AI) → Transformed image returned → Displayed in UI
3. **Individual Style Barber Search**: User clicks "Find Barbers" → Google Places API search for that style
4. **General Barber Search**: Location input → Geocoding → Places API → Enhanced results with specialties
5. **Subscription Management**: Barbers create packages → Stored in backend → Clients view and subscribe
6. **Rate Limiting**: Daily API quotas tracked server-side with graceful fallbacks

## Development Guidelines

### API Integration Patterns
- **Graceful Degradation**: Always provide fallback mock data when external APIs fail
- **Rate Limiting Awareness**: Backend tracks daily API usage to prevent quota exhaustion
- **Error Handling**: Comprehensive try-catch blocks with meaningful error messages

### Frontend State Management
- **Global State Variables**: `currentUserMode`, `lastRecommendedStyles`, `socialPosts`, etc.
- **Event-Driven Updates**: UI components re-render when underlying data changes
- **Modal Dialog Management**: Centralized show/hide logic with cleanup functions

### Image Handling
- **Client-Side Compression**: Images resized to max 800px before upload
- **Base64 Encoding**: Used for API transmission to Gemini
- **Fallback Images**: Placeholder URLs when image loads fail

### Location Services
- **Flexible Input**: Supports ZIP codes, city names, neighborhoods
- **Caching System**: Places API results cached for 1 hour to reduce API calls
- **Search Enhancement**: Recommended styles passed to barber search for better matching

## Code Quality Standards

### Python (Backend)
- Use type hints where beneficial
- Comprehensive error handling with logging
- Rate limiting on all user-facing endpoints
- Environment variable configuration for API keys
- Mock data fallbacks for development and API failures

### JavaScript (Frontend)
- ES6+ syntax and patterns
- Async/await for API calls
- Event delegation for dynamic content
- Responsive design principles
- Accessibility considerations for dialogs and forms

### Security Considerations
- CORS properly configured for production domains
- API keys stored as environment variables, never in code
- Rate limiting to prevent abuse
- Input validation on all endpoints
- No sensitive data in frontend JavaScript

## Platform-Specific Notes

### Render Deployment
- **Backend**: Deployed as web service with gunicorn
- **Frontend**: Deployed as static site
- **Environment Variables**: Configure GEMINI_API_KEY and GOOGLE_PLACES_API_KEY in Render dashboard
- **Health Checks**: `/health` endpoint provides deployment status

### External Dependencies
- **Google Gemini AI**: Powers facial analysis and haircut recommendations
- **Google Places API**: Provides real barbershop data with photos, ratings, hours
- **Unsplash**: Used for placeholder images and mock data photos
- **TailwindCSS CDN**: Styling framework loaded from CDN

## Testing Approach

### Manual Testing Workflow
1. **Image Analysis**: Test with various face angles and lighting conditions
2. **Virtual Try-On**: Upload a photo → Select hairstyle → Verify transformed image displays (works without API key via PIL fallback)
3. **Subscription Packages**: In Barber mode, create packages and verify they display correctly
4. **Location Search**: Verify with different location formats (ZIP, city, neighborhood)
5. **Role Switching**: Ensure all tabs and features work in both Client/Barber modes
6. **Responsive Design**: Test on mobile and desktop screen sizes
7. **API Fallbacks**: Test behavior when external APIs are unavailable

### Common Issues and Solutions
- **CORS Errors**: Ensure API_URL in frontend matches deployed backend URL
- **Image Upload Issues**: Check file size limits and supported formats
- **API Rate Limits**: Monitor `/health` endpoint for usage tracking
- **Location Search Problems**: Verify Google Places API key and billing setup
- **Virtual Try-On Not Working**: 
  - Virtual try-on works immediately with preview mode (no setup required!)
  - Check browser console (F12 → Network tab) for any errors
  - **Optional AI Enhancement**: See `HAIR_TRYON_SETUP.md`
    - Get FREE Replicate API token: https://replicate.com/account/api-tokens
    - Add `REPLICATE_API_TOKEN` to environment variables
    - Takes 5 minutes, costs ~$3/month for 100 users
