# LineUp AI - v2.0

**AI-Powered Haircut Analysis & Barber Booking Platform**

## Overview

LineUp is a two-sided AI-powered haircut analysis and barber platform that helps users find the perfect haircut and connects them with barbershops in their area.

- **Frontend**: Vanilla HTML/CSS/JavaScript with TailwindCSS (single-page application)
- **Backend**: Flask API with Google Gemini AI integration and Google Places API
- **Database**: Firebase Cloud Firestore with automatic fallback to in-memory storage
- **Deployment**: Render (frontend and backend hosted separately)

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Flask backend
python app.py
# Backend runs on http://localhost:5000

# For frontend development
# Open index.html directly in browser or use a local server:
python -m http.server 8000
# Frontend accessible at http://localhost:8000
```

**Minimum requirement:** Add `GEMINI_API_KEY` to environment variables (free at https://makersuite.google.com)

## Environment Variables

Required for full functionality:

- See `ENVIRONMENT_SETUP.md` for a full checklist and rate-limit overrides.

- `GEMINI_API_KEY`: Google Gemini API key for AI hair analysis (required)
- `GOOGLE_PLACES_API_KEY`: Google Places API key for real barber shop data (optional)
- `FIREBASE_CREDENTIALS`: Firebase service account JSON for persistent storage (optional)
- `REPLICATE_API_TOKEN`: Replicate API key for AI hair transformation enhancement (optional)
- `HF_TOKEN`: Hugging Face token for HairFastGAN (optional)
- `PORT`: Port for Flask app (defaults to 5000)

**Virtual Try-On**: Works immediately with preview mode. No API keys required for basic functionality. See `HAIR_TRYON_SETUP.md` for optional AI enhancement.

## Features

### Client Mode
- Upload photo for AI-powered facial analysis
- Receive personalized haircut recommendations based on face shape, hair texture, and features
- Virtual try-on with preview mode (works immediately, no setup required)
- Find barbershops by location with real-time data from Google Places API
- Search for barbers specializing in specific haircut styles
- View barber reviews and ratings
- Book appointments
- Browse social feed with posts, likes, comments, and shares

### Barber Mode
- Manage portfolio of work
- Create subscription packages
- View and manage appointments
- Track client subscriptions

## Architecture

### Backend (`app.py`)

Flask REST API with the following components:

- **Rate Limiting**: Flask-Limiter with 1000 requests/hour default limit
- **AI Analysis**: Google Gemini 2.0 Flash model for facial/hair analysis
- **Database**: Firebase Cloud Firestore with automatic fallback to in-memory storage
- **External APIs**: 
  - Google Places API for barbershop discovery
  - Google Gemini for AI analysis
  - Replicate (optional) for AI hair transformation
  - HairFastGAN via Gradio Client (optional, free but unreliable)
- **Image Processing**: PIL/Pillow for virtual try-on preview mode
- **CORS**: Enabled for cross-origin requests
- **Error Handling**: Comprehensive fallbacks when APIs are unavailable

### API Endpoints

- `GET /` - Service information and status
- `GET /health` - System health check and API usage tracking
- `GET /config` - Configuration and API availability status
- `POST /analyze` - AI haircut analysis (10 requests/hour limit)
- `POST /virtual-tryon` - Virtual hair try-on with preview mode (20 requests/hour limit)
- `GET /barbers?location=...` - Search barbershops by location via Google Places API
- `GET /social` - Get all social posts
- `POST /social` - Create new social post
- `POST /social/<post_id>/like` - Like/unlike a post
- `POST /social/<post_id>/comments` - Add comment to a post
- `POST /social/<post_id>/share` - Share a post
- `GET /appointments` - Get appointments (filter by user type and ID)
- `POST /appointments` - Create new appointment
- `PUT /appointments/<id>/status` - Update appointment status
- `GET /portfolio` or `GET /portfolio/<barber_id>` - Get barber portfolio
- `POST /portfolio` or `POST /portfolio/<barber_id>` - Add work to portfolio
- `GET /barbers/<barber_id>/reviews` - Get reviews for a barber
- `POST /barbers/<barber_id>/reviews` - Add review for a barber
- `POST /users/<user_id>/follow` - Follow a user
- `DELETE /users/<user_id>/unfollow` - Unfollow a user
- `GET /subscription-packages` - Get subscription packages
- `POST /subscription-packages` - Create subscription package
- `GET /client-subscriptions` - Get client subscriptions
- `POST /client-subscriptions` - Create client subscription
- `GET /ai-insights` - Get AI-generated hair trends and recommendations

### Frontend (`index.html` + `scripts-updated.js`)

Single-page application with:

- **Role-based UI**: Switch between Client and Barber modes
- **Tab Navigation**: AI Analysis, Virtual Try-On, Social Feed, Barbers, Appointments
- **Image Upload**: Client-side compression and base64 encoding
- **Real-time Updates**: Dynamic UI updates without page refreshes
- **Responsive Design**: Works on mobile and desktop using TailwindCSS
- **Modal Dialogs**: For image uploads, appointments, and reviews

## Database

### Firebase/Firestore

The application uses Firebase Cloud Firestore for persistent data storage. If Firebase is not configured, it automatically falls back to in-memory storage.

**Collections:**
- `social_posts` - Social media posts
- `appointments` - Appointment bookings
- `barber_portfolios` - Barber work portfolios
- `barber_reviews` - Reviews for barbers
- `post_comments` - Comments on social posts
- `user_follows` - User follow relationships
- `subscription_packages` - Barber subscription packages
- `client_subscriptions` - Active client subscriptions

**Setup:**
1. Create a Firebase project at https://console.firebase.google.com
2. Enable Firestore Database
3. Generate service account credentials
4. Add credentials JSON to `FIREBASE_CREDENTIALS` environment variable

If `FIREBASE_CREDENTIALS` is not set, the app uses in-memory storage (data resets on restart).

## Virtual Try-On

The virtual try-on feature works immediately without any API keys using preview mode:

1. User uploads a photo
2. Selects a hairstyle from recommendations
3. Backend processes the image and adds a text overlay showing the style name
4. Returns the preview image with overlay

**Optional Enhancements:**
- **HairFastGAN**: Free but unreliable Hugging Face model. Set `HF_TOKEN` environment variable.
- **Replicate**: More reliable paid option. Set `REPLICATE_API_TOKEN` environment variable.

See `HAIR_TRYON_SETUP.md` for detailed setup instructions.

## Testing

### Test Backend Endpoints

```bash
# Health check
curl http://localhost:5000/health

# AI analysis (requires image data)
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"payload": {"contents": [{"parts": [{"text": "analyze"}, {"inlineData": {"mimeType": "image/jpeg", "data": "base64data"}}]}]}}'

# Barber search
curl "http://localhost:5000/barbers?location=Atlanta,GA"

# Virtual try-on
curl -X POST http://localhost:5000/virtual-tryon \
  -H "Content-Type: application/json" \
  -d '{"userPhoto": "base64data", "styleDescription": "Side Part with Volume"}'
```

## Deployment

### Render Deployment

**Backend:**
1. Connect GitHub repository to Render
2. Create new Web Service
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Add environment variables in Render dashboard

**Frontend:**
1. Create new Static Site on Render
2. Connect to repository
3. Set build command: (none needed for static files)
4. Set publish directory: `/` (or wherever index.html is located)

### Environment Variables on Render

Add all required environment variables in the Render dashboard under your service settings.

## Rate Limiting

The backend implements rate limiting to prevent API abuse:

- Global limit: 1000 requests/hour per IP
- AI Analysis: 10 requests/hour per IP
- Social posts: 20 requests/hour per IP
- Appointments: 30 requests/hour per IP
- Barber search: 50 requests/hour per IP
- Virtual try-on: 20 requests/hour per IP

## Error Handling

The application implements comprehensive error handling:

- Graceful fallbacks to mock data when external APIs fail
- Daily API usage tracking to prevent quota exhaustion
- Detailed logging for debugging
- User-friendly error messages
- Automatic retry logic where appropriate

## Development Guidelines

### Code Standards

**Backend (Python):**
- Comprehensive error handling with logging
- Rate limiting on all endpoints
- Environment variable configuration
- Mock data fallbacks for development
- CORS properly configured

**Frontend (JavaScript):**
- ES6+ syntax with async/await
- Event delegation for dynamic content
- Responsive design principles
- Client-side image compression
- Error handling for API calls

### Security

- API keys stored as environment variables
- CORS configured for production domains
- Rate limiting to prevent abuse
- Input validation on all endpoints
- No sensitive data in frontend code

## Documentation

- `HAIR_TRYON_SETUP.md` - Virtual try-on setup guide
- `FREE_HAIR_TRYON_SETUP.md` - Free hair try-on options
- `HAIRFASTGAN_VERIFICATION.md` - HairFastGAN integration details

## Project Structure

```
LineUp/
├── app.py                 # Main Flask backend application
├── index.html            # Frontend HTML
├── scripts-updated.js    # Frontend JavaScript
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── [other .md files]    # Additional documentation
```

## Support

For issues or questions:
1. Check the `/health` endpoint for system status
2. Review application logs on Render dashboard
3. Verify environment variables are set correctly
4. Check API quotas and rate limits

## License

This project is available for use as specified in the repository.
