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
- `MODAL_HAIRFAST_ENDPOINT`: Modal Labs endpoint for HairFastGAN transformations (FREE $30/month credit!)
- `HF_API_KEY`: Hugging Face API key (alternative to Modal for HairFastGAN)
- `PORT`: Port for Flask app (defaults to 5000)

**For Virtual Try-On Setup**: See `HAIRFAST_SETUP.md` for detailed instructions on deploying HairFastGAN

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
- `/virtual-tryon` - **Visual hair transformation using HairFastGAN** (20 req/hour limit)
  - Requires `MODAL_HAIRFAST_ENDPOINT` or `HF_API_KEY` to be configured
  - Returns actual transformed image, not just text advice
  - See `HAIRFAST_SETUP.md` for deployment instructions
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
- **Modal system** for image uploads, posts, and appointments
- **Real-time UI updates** without page refreshes

#### Key Components
- **Role Switcher**: Toggle between Client/Barber modes
- **AI Analysis Flow**: Image upload → compression → Gemini API → structured recommendations
- **Virtual Try-On**: Upload photo → Select hairstyle → **HairFastGAN GPU transformation** → actual visual result
  - Uses Modal Labs serverless GPU (FREE $30/month credit)
  - Returns transformed image showing new hairstyle on user's photo
  - Fallback to Hugging Face API if Modal not configured
- **Subscription Packages**: Barbers create subscription deals (e.g., 2 cuts/month for $X)
- **Individual Style Barber Search**: Each recommendation has "Find Barbers" button
- **Barber Discovery**: Location-based search with Google Places API
- **Social Feed**: Community posts with like/comment functionality
- **Appointment System**: Booking interface with real-time availability

### Data Flow Patterns
1. **Image Analysis**: Frontend compresses images → Base64 encoding → Gemini API → Structured recommendations
2. **Virtual Try-On**: User photo (base64) + style description → Backend `/virtual-tryon` → **Modal Labs HairFastGAN GPU** → Actual transformed image returned → Displayed in UI
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
  - Check browser console (F12 → Network tab) for endpoint errors
  - Verify `/virtual-tryon` endpoint returns 503 with setup instructions if not configured
  - **Setup Required**: See `HAIRFAST_SETUP.md` for deploying HairFastGAN
  - **Option 1 (Recommended)**: Deploy to Modal Labs ($30/month FREE credit)
    - Run `modal deploy modal_hairfast.py`
    - Set `MODAL_HAIRFAST_ENDPOINT` environment variable
  - **Option 2**: Use Hugging Face Inference API
    - Get API key from https://huggingface.co/settings/tokens
    - Set `HF_API_KEY` environment variable
  - Without either endpoint configured, virtual try-on will show setup instructions
