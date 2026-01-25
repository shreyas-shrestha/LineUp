# Render Deployment Checklist for v2

## ✅ Pre-Deployment Checklist

### 1. Code is Ready
- [x] v2 branch pushed to GitHub
- [x] All dependencies in requirements.txt
- [x] Blueprints registered in app.py
- [x] Error handlers registered

### 2. Firebase Setup
- [x] Firebase project created
- [x] Firestore Database enabled
- [x] Service account credentials downloaded

### 3. Render Configuration

#### Step 1: Switch Branch
1. Go to Render Dashboard → Your Backend Service
2. Go to Settings tab
3. Change "Branch" from `main` to `v2`
4. Save

#### Step 2: Add Firebase Credentials
1. Go to Environment tab
2. Click "Add Environment Variable"
3. Key: `FIREBASE_CREDENTIALS`
4. Value: Run `python3 prepare_render_credentials.py` locally and copy the output
   - Or manually convert your JSON file to a single-line string
5. Save

#### Step 3: Verify Other Environment Variables
Make sure these are set (if you use them):
- `GEMINI_API_KEY` ✅
- `GOOGLE_PLACES_API_KEY` ✅
- `REPLICATE_API_TOKEN` (optional)
- `CLOUDINARY_CLOUD_NAME` (optional)
- `CLOUDINARY_API_KEY` (optional)
- `CLOUDINARY_API_SECRET` (optional)

### 4. Deploy

1. Go to Manual Deploy tab
2. Click "Deploy latest commit"
3. Wait for build to complete
4. Check logs for:
   - ✅ "Firebase Admin SDK loaded successfully"
   - ✅ "Firebase Firestore initialized successfully"
   - ✅ "Error handlers registered successfully"
   - ✅ "v2 blueprints (auth, analyze) registered successfully"

## 🧪 Testing After Deployment

### Test Health Endpoint
```bash
curl https://your-render-url.onrender.com/health
```

### Test Auth Endpoint (should return 401)
```bash
curl https://your-render-url.onrender.com/auth/me
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

### Test Social Feed (should work without auth)
```bash
curl https://your-render-url.onrender.com/social
```

## 🔍 Troubleshooting

### Build Fails
- Check that all dependencies in requirements.txt are valid
- Check Render build logs for specific errors

### Firebase Not Connecting
- Verify FIREBASE_CREDENTIALS is set correctly (single-line JSON string)
- Check Render logs for Firebase initialization errors
- Verify Firestore is enabled in Firebase Console

### 500 Errors
- Check Render logs for Python errors
- Verify all environment variables are set
- Check that Firestore security rules allow access

### Auth Endpoints Not Working
- Verify blueprints are registered (check startup logs)
- Check that error handlers are registered
- Verify CORS is configured correctly

## 📝 Quick Reference

**Get Firebase Credentials String:**
```bash
python3 prepare_render_credentials.py
```

**Check Render Logs:**
- Render Dashboard → Your Service → Logs tab

**Redeploy:**
- Render Dashboard → Manual Deploy → Deploy latest commit

## ✅ What's New in v2

- Database layer with Firestore
- Authentication endpoints (`/auth/*`)
- Save analysis endpoints (`/analyze/save`, `/analyze/history`)
- All data persists in Firestore
- Better error handling

## 🚀 After Deployment

Once deployed, your app will:
1. Connect to Firestore automatically
2. Create collections as needed
3. Persist all data
4. Support user authentication
5. Allow saving analysis results
