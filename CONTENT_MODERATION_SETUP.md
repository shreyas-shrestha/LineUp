# Content Moderation & Image Storage Setup Guide

## Overview
This guide explains how to set up content moderation and image storage for the community feed.

## Features Implemented

### 1. Image Storage (Firebase Storage)
- Images are uploaded to Firebase Storage instead of storing base64 in database
- Each image gets a unique filename with timestamp
- Images are stored in `community-posts/` folder
- Public URLs are stored in Firestore for fast access

### 2. Content Moderation
- **Explicit Content Filtering**: Uses Gemini Vision API to detect inappropriate content
- **Hair-Related Content Filtering**: Validates that posts are actually about hair/hairstyles

### 3. Moderation Process
When a user posts an image:
1. Image is decoded from base64
2. Uploaded to Firebase Storage (if configured)
3. Content moderation checks run:
   - Check for explicit/inappropriate content
   - Verify image is hair-related
4. If approved: Post is saved to database
5. If rejected: User receives specific error message

## Setup Steps

### Step 1: Enable Firebase Storage

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Navigate to **Storage** in the left sidebar
4. Click **Get Started**
5. Choose security rules (start with test mode for development)
6. Select storage location

### Step 2: Update Firebase Credentials

Your existing `FIREBASE_CREDENTIALS` environment variable should already have storage permissions. If not:

1. Go to Firebase Console > Project Settings > Service Accounts
2. Generate new private key
3. Update `FIREBASE_CREDENTIALS` environment variable with the new JSON

**Note**: The service account needs these permissions:
- Cloud Firestore User
- Storage Object Admin (for uploading files)

### Step 3: Install Additional Dependencies

```bash
pip install google-cloud-storage
```

Add to `requirements.txt`:
```
google-cloud-storage==2.14.0
```

### Step 4: Configure Environment Variables

No additional environment variables needed! The system uses:
- `FIREBASE_CREDENTIALS` (already configured)
- `GEMINI_API_KEY` (already configured for content moderation)

### Step 5: Test the Moderation

1. Try posting a hair-related image → Should be approved
2. Try posting a non-hair image → Should be rejected with message
3. Try posting explicit content → Should be rejected with message

## How It Works

### Image Storage Flow
```
User uploads image (base64)
  ↓
Backend decodes to bytes
  ↓
Upload to Firebase Storage → Returns public URL
  ↓
Store URL in Firestore (not base64)
```

### Content Moderation Flow
```
Image received
  ↓
Moderation checks:
  1. Explicit content? → Reject if found
  2. Hair-related? → Reject if not hair-related
  ↓
If approved → Save to database
If rejected → Return error to user
```

## Moderation Rules

### Explicit Content Detection
The system checks for:
- Adult content
- Violence
- Racy content
- Medical content (inappropriate)
- Spoof content

### Hair-Related Detection
The system checks if the image contains:
- Haircuts
- Hairstyles
- Hair coloring/processing
- Barber/stylist work
- Hair products/styling

Rejects images of:
- Random objects
- Landscapes
- Animals (unless showing hair styling)
- Unrelated people/activities

## Fallback Behavior

If Firebase Storage is not configured:
- Images are still stored as base64 (current behavior)
- Content moderation still runs
- Posts can still be filtered

If Gemini API is not available:
- Moderation is skipped (permissive mode)
- Warning logged
- Post is accepted (for development/testing)

## API Endpoints

### POST /social
Enhanced with content moderation:
- Validates image before saving
- Returns specific error messages for rejected content

Response for rejection:
```json
{
  "success": false,
  "error": "Content rejected",
  "reason": "Image is not hair-related" | "Inappropriate content detected"
}
```

## Production Recommendations

1. **Enable Firebase Storage** - Essential for production
2. **Set up proper storage rules** - Restrict who can upload/read
3. **Enable Cloud Functions** - For additional moderation checks
4. **Set up moderation queue** - For manual review of edge cases
5. **Add image optimization** - Compress images before storage
6. **Rate limit uploads** - Prevent spam/abuse

## Monitoring

Check logs for moderation decisions:
- `INFO: Content moderation: Approved`
- `WARNING: Content moderation: Rejected - [reason]`
- `ERROR: Content moderation failed: [error]`

