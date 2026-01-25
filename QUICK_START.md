# Quick Start - LineUp v2 Database Setup

## 🚀 Fast Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Firebase Credentials

**Option A: Quick Setup Script**
```bash
# Download your Firebase service account JSON file from Firebase Console
# Then run:
python3 set_firebase_env.py your-firebase-credentials.json
python3 app.py
```

**Option B: Manual Setup**
```bash
# Export the JSON as a string
export FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"...",...}'
python3 app.py
```

### 3. Verify Setup
```bash
python3 test_setup.py
```

### 4. Start Server
```bash
python3 app.py
```

## 📋 Firebase Setup Checklist

- [ ] Created Firebase project at https://console.firebase.google.com
- [ ] Enabled Firestore Database (test mode is fine for dev)
- [ ] Generated service account key (Project Settings → Service Accounts)
- [ ] Downloaded JSON credentials file
- [ ] Set `FIREBASE_CREDENTIALS` environment variable

## 🧪 Test It Works

```bash
# Health check
curl http://localhost:5000/health

# Auth endpoint (should return 401 - that's good!)
curl http://localhost:5000/auth/me

# Social feed (should work without auth)
curl http://localhost:5000/social
```

## 🔧 Development Mode (No Firebase)

```bash
export LINEUP_DISABLE_AUTH=true
export FLASK_ENV=development
python3 app.py
```

## 📚 Full Documentation

See `V2_SETUP_GUIDE.md` for detailed instructions.

## ✅ What's Ready

- ✅ Database layer with Firestore
- ✅ Authentication system
- ✅ Save analysis endpoints
- ✅ User management endpoints
- ✅ All repositories created

## 🎯 Next Steps

1. Set up Firebase credentials
2. Test the endpoints
3. Integrate Firebase Auth SDK in frontend
4. Continue with Phase 3 (validation) and Phase 4 (analytics)
