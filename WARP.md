# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

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
- `GEMINI_API_KEY`: Google Gemini API key for AI analysis
- `GOOGLE_PLACES_API_KEY`: Google Places API key for real barber data
- `PORT`: Port for Flask app (defaults to 5000)

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
- `/analyze` - AI haircut analysis (10 req/hour limit)
- `/barbers` - Real barbershop search with location
- `/social` - Social media feed functionality  
- `/appointments` - Appointment booking and management
- `/portfolio` - Barber portfolio management
- `/health` - System health and API usage tracking

### Frontend Architecture (`index.html` + `scripts-updated.js`)
- **Single-page application** with role-based content switching
- **Tab-based navigation** for different features
- **Responsive design** using TailwindCSS
- **Modal system** for image uploads, posts, and appointments
- **Real-time UI updates** without page refreshes

#### Key Components
- **Role Switcher**: Toggle between Client/Barber modes
- **AI Analysis Flow**: Image upload → compression → API call → results display with improved UI and proper capitalization
- **Individual Style Barber Search**: Each haircut recommendation has its own "Find Barbers" button for targeted searches
- **Barber Discovery**: Location-based search with Google Places integration and enhanced UI feedback
- **Social Feed**: Community posts with like/comment functionality
- **Appointment System**: Booking interface with real-time availability

### Data Flow Patterns
1. **Image Analysis**: Frontend compresses images → Base64 encoding → Gemini API → Structured recommendations with individual barber search buttons
2. **Individual Style Barber Search**: User clicks "Find Barbers" on specific haircut → Search for barbers specializing in that style
3. **General Barber Search**: Location input → Geocoding → Places API → Enhanced results with specialties
4. **Rate Limiting**: Daily API quotas tracked server-side with graceful fallbacks

## Development Guidelines

### API Integration Patterns
- **Graceful Degradation**: Always provide fallback mock data when external APIs fail
- **Rate Limiting Awareness**: Backend tracks daily API usage to prevent quota exhaustion
- **Error Handling**: Comprehensive try-catch blocks with meaningful error messages

### Frontend State Management
- **Global State Variables**: `currentUserMode`, `lastRecommendedStyles`, `socialPosts`, etc.
- **Event-Driven Updates**: UI components re-render when underlying data changes
- **Modal Management**: Centralized show/hide logic with cleanup functions

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
- Accessibility considerations for modals and forms

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
2. **Location Search**: Verify with different location formats (ZIP, city, neighborhood)
3. **Role Switching**: Ensure all tabs and features work in both Client/Barber modes
4. **Responsive Design**: Test on mobile and desktop screen sizes
5. **API Fallbacks**: Test behavior when external APIs are unavailable

### Common Issues and Solutions
- **CORS Errors**: Ensure API_URL in frontend matches deployed backend URL
- **Image Upload Issues**: Check file size limits and supported formats
- **API Rate Limits**: Monitor `/health` endpoint for usage tracking
- **Location Search Problems**: Verify Google Places API key and billing setup
