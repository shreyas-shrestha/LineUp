# Firebase/Firestore Setup for LineUp

## Overview

LineUp now uses **Firebase Cloud Firestore** as its database, with automatic fallback to in-memory storage if Firebase is not configured. This provides:

- ✅ Persistent data storage
- ✅ Real-time database
- ✅ Scalable cloud infrastructure
- ✅ Fallback to in-memory for development
- ✅ Zero configuration required to get started

## Setup Steps

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project"
3. Enter project name: `lineup-ai` (or your choice)
4. Disable Google Analytics (optional)
5. Click "Create project"

### 2. Create Firestore Database

1. In your Firebase project, click "Firestore Database" in the left menu
2. Click "Create database"
3. Choose location: `us-central` (or closest to your deployment)
4. Start in **Production mode**
5. Click "Enable"

### 3. Generate Service Account

1. Go to Project Settings (gear icon)
2. Click "Service accounts" tab
3. Click "Generate new private key"
4. Save the JSON file as `firebase-credentials.json`

### 4. Add Credentials to Render

#### Option A: Environment Variable (Recommended)

1. Open your JSON credentials file
2. Copy the entire JSON content
3. In Render dashboard → Environment Variables
4. Add new variable:
   - **Key**: `FIREBASE_CREDENTIALS`
   - **Value**: Paste the entire JSON (it will be automatically JSON-stringified)

#### Option B: Upload Credentials File

1. Store `firebase-credentials.json` in your project root
2. Add to `.gitignore` (IMPORTANT!)
3. In Render, you can use file-based authentication

### 5. Firestore Rules (Security)

In Firebase Console → Firestore Database → Rules, use:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read access to all documents
    match /{document=**} {
      allow read: if true;
      
      // Only allow writes from authenticated users or your backend
      allow write: if request.auth != null || 
                     request.headers.authorization == 'YOUR_SECRET_KEY';
    }
  }
}
```

**For development/testing**, you can temporarily use:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

⚠️ **WARNING**: The second rule allows anyone to write. Only use for testing!

## Collections Structure

Firestore uses a document-based NoSQL structure. Here are the collections used:

### `social_posts`
- Document fields: `id`, `username`, `avatar`, `image`, `caption`, `likes`, `shares`, `comments`, `timestamp`, `hashtags`, `liked`

### `appointments`
- Document fields: `id`, `clientName`, `clientId`, `barberName`, `barberId`, `date`, `time`, `service`, `price`, `status`, `notes`, `timestamp`

### `barber_portfolios`
- Collection: `barber_portfolios/{barber_id}/works`
- Document fields: `id`, `styleName`, `image`, `description`, `likes`, `date`, `barberId`

### `barber_reviews`
- Collection: `barber_reviews/{barber_id}`
- Subcollection: `reviews/{review_id}`
- Document fields: `id`, `username`, `rating`, `text`, `date`

### `post_comments`
- Collection: `post_comments/{post_id}/comments`
- Document fields: `id`, `username`, `text`, `timeAgo`, `timestamp`

### `user_follows`
- Collection: `user_follows/{user_id}/follows`
- Document fields: `followed_user_id`

### `subscription_packages`
- Document fields: All subscription details

### `client_subscriptions`
- Document fields: All active subscription details

## Testing

### Without Firebase (Development)

The app works perfectly without Firebase using in-memory storage. No configuration needed!

### With Firebase (Production)

1. Set up Firebase project
2. Add `FIREBASE_CREDENTIALS` to environment variables
3. Redeploy on Render
4. Check logs for: `"Firebase initialized with credentials from environment"`

## Monitoring

### Firebase Console

- View all documents in real-time
- Monitor database usage
- See read/write statistics
- Set up usage alerts

### Application Logs

Look for these log messages:
- `"Firebase Admin SDK loaded successfully"` - Firebase installed
- `"Firebase initialized with credentials from environment"` - Firebase configured
- `"Firebase not installed. Will use in-memory storage."` - Using fallback
- `"FIREBASE_CREDENTIALS not found - will use in-memory storage"` - No credentials

## Cost Estimates

Firebase Spark Plan (Free):
- **5GB** storage
- **1GB/day** network egress
- **50K reads/day**
- **20K writes/day**
- **20K deletes/day**

This should be more than enough for early stages!

## Troubleshooting

### "Firebase initialization failed"

1. Check JSON credentials are valid
2. Verify environment variable is set correctly
3. Check service account has Firestore permissions

### "Permission denied"

1. Check Firestore security rules
2. Verify service account has correct role
3. Check database is enabled

### Data not persisting

1. Check if `db` is initialized (logs should show Firebase initialized)
2. Verify Firestore rules allow writes
3. Check Firebase Console for errors

## Migration from In-Memory

The app automatically uses Firestore when configured. Existing in-memory data can be manually imported:

1. Export current data from `/health` endpoint
2. Use Firebase Console to manually create documents
3. Or write a one-time migration script

## Next Steps

- [ ] Set up Firebase project
- [ ] Configure Firestore database
- [ ] Add credentials to Render
- [ ] Test data persistence
- [ ] Set up Firestore security rules
- [ ] Monitor usage and costs
- [ ] Migrate remaining endpoints to Firestore

## Support

- [Firebase Documentation](https://firebase.google.com/docs)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Admin SDK Documentation](https://firebase.google.com/docs/admin/setup)

