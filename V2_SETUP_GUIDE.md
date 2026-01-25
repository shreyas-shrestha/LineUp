# LineUp v2 Setup Guide

This guide will help you set up the v2 database layer and authentication system.

## Prerequisites

- Python 3.11+
- Firebase project (free tier works)
- Firebase Admin SDK credentials

## Step 1: Install Dependencies

All dependencies are already in `requirements.txt`. Make sure they're installed:

```bash
pip install -r requirements.txt
```

## Step 2: Firebase Setup

### 2.1 Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project" or select existing project
3. Follow the setup wizard
4. Enable **Firestore Database**:
   - Go to "Firestore Database" in the sidebar
   - Click "Create database"
   - Choose "Start in test mode" (for development)
   - Select a location (choose closest to your users)

### 2.2 Get Service Account Credentials

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Go to **Service Accounts** tab
3. Click **Generate new private key**
4. Download the JSON file (e.g., `lineup-firebase-adminsdk.json`)

### 2.3 Set Environment Variable

**Option A: Export directly (temporary)**
```bash
export FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"your-project-id",...}'
```

**Option B: Use a JSON file (recommended for local dev)**

Create a helper script `set_firebase_env.py`:

```python
import json
import os

# Read the JSON file
with open('lineup-firebase-adminsdk.json', 'r') as f:
    creds = json.load(f)

# Set as environment variable (JSON string)
os.environ['FIREBASE_CREDENTIALS'] = json.dumps(creds)
print("✅ FIREBASE_CREDENTIALS set from JSON file")
```

Then run:
```bash
python set_firebase_env.py
python app.py
```

**Option C: For Render/Production**

In Render dashboard:
1. Go to your service → Environment
2. Add environment variable:
   - Key: `FIREBASE_CREDENTIALS`
   - Value: Paste the entire JSON content as a single-line string

## Step 3: Verify Setup

Run the test script:

```bash
python test_setup.py
```

You should see:
- ✅ All imports successful
- ✅ Firestore is available and connected
- ✅ FIREBASE_CREDENTIALS is set
- ✅ All repositories can be instantiated

## Step 4: Start the Server

```bash
python app.py
```

You should see logs like:
```
INFO: Firebase Admin SDK loaded successfully
INFO: Firebase Firestore initialized successfully
INFO: Error handlers registered successfully
INFO: v2 blueprints (auth, analyze) registered successfully
🚀 Starting LineUp API server on port 5000
```

## Step 5: Test Endpoints

### Test Health Endpoint
```bash
curl http://localhost:5000/health
```

### Test Auth Endpoint (should return 401)
```bash
curl http://localhost:5000/auth/me
```

Expected response:
```json
{
  "success": false,
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Missing authentication token"
  }
}
```

### Test Optional Auth Endpoint (should work)
```bash
curl http://localhost:5000/social
```

Should return posts (empty array if no posts yet).

## Development Mode (No Firebase Required)

If you want to test without Firebase:

```bash
export LINEUP_DISABLE_AUTH=true
export FLASK_ENV=development
python app.py
```

This will:
- Skip Firebase authentication checks
- Create mock users for testing
- Use in-memory storage (data resets on restart)

## Troubleshooting

### "Firebase Admin SDK not available"
- Install: `pip install firebase-admin`

### "FIREBASE_CREDENTIALS not found"
- Make sure you've set the environment variable
- Check that the JSON is valid: `python -c "import json; json.loads(os.environ['FIREBASE_CREDENTIALS'])"`

### "Firestore not available"
- Check Firebase project has Firestore enabled
- Verify credentials have correct permissions
- Check project_id matches your Firebase project

### "Permission denied" errors
- Make sure Firestore is in "test mode" for development
- Or set up proper security rules in Firebase Console

## What's Working Now

✅ **Database Layer:**
- Firestore client wrapper
- Repository pattern for all collections
- Pydantic models for type safety

✅ **Authentication:**
- User registration (`POST /auth/register`)
- Get current user (`GET /auth/me`)
- Update profile (`PUT /auth/me`)
- Role management (`POST /auth/role`)

✅ **Save Analysis:**
- Save analysis results (`POST /analyze/save`)
- Get analysis history (`GET /analyze/history`)
- Get specific analysis (`GET /analyze/<id>`)
- Delete analysis (`DELETE /analyze/<id>`)

## Next Steps

1. **Integrate Firebase Auth SDK in Frontend** - For user login/registration
2. **Migrate Existing Routes** - Update `/social`, `/appointments` to use repositories
3. **Phase 3: Input Validation** - Add Pydantic validation to all endpoints
4. **Phase 4: Barber Analytics** - Build metrics tracking system

## Firestore Collections Created Automatically

When you start using the endpoints, these collections will be created:
- `users` - User profiles
- `saved_analyses` - Saved haircut analyses
- `social_posts` - Social feed posts
- `post_comments` - Comments on posts
- `post_likes` - Like records
- `user_follows` - Follow relationships
- `appointments` - Appointment bookings
- `barber_portfolios` - Barber work portfolios
- `barber_reviews` - Reviews for barbers
- `barber_metrics` - Analytics metrics
- `barber_events` - Event tracking
- `notifications` - User notifications

## Security Notes

- **Never commit** `FIREBASE_CREDENTIALS` or service account JSON files to git
- Use environment variables for all secrets
- In production, use Firebase Security Rules to restrict access
- Enable Firebase Authentication for user login (separate from Admin SDK)
