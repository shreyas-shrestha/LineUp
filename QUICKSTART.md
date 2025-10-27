# 🚀 Quick Start Guide - LineUp AI v2.0

Get up and running in **5 minutes** with all the new improvements!

---

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A text editor

---

## ⚡ Installation (2 minutes)

### Option 1: Automated Setup (Recommended)
```bash
# Run the setup script
python setup.py
```

The script will:
- ✅ Install all dependencies
- ✅ Create .env configuration file
- ✅ Initialize SQLite database
- ✅ Validate configuration
- ✅ Run tests

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy environment template
cp env.example.txt .env

# 3. Edit .env and add your API keys (minimum: GEMINI_API_KEY)
nano .env  # or use any text editor

# 4. Initialize database (automatic on first run)
python app_refactored.py
```

---

## 🔑 Get Free API Keys (3 minutes)

### Minimum Setup (Required):

**1. Google Gemini API** (for AI hair analysis):
- Visit: https://makersuite.google.com/app/apikey
- Click "Create API Key"
- Copy key to .env file: `GEMINI_API_KEY=your_key_here`
- **Free tier:** 60 requests/minute

**That's it!** The app will work with this one key. Everything else uses mock data.

### Optional Enhancements:

**2. Google Places API** (for real barber discovery):
- Visit: https://console.cloud.google.com/apis/credentials
- Create credentials → API key
- Enable "Places API" and "Geocoding API"
- Copy key to .env: `GOOGLE_PLACES_API_KEY=your_key_here`
- **Free tier:** $200/month credit (~40k searches)

**3. Modal Labs** (for real hair transformations):
- Visit: https://modal.com
- Sign up (GitHub login)
- Deploy HairFastGAN: `modal deploy modal_hairfast.py`
- Copy endpoint URL to .env: `MODAL_HAIRFAST_ENDPOINT=your_url_here`
- **Free tier:** $30/month GPU credits

---

## 🎯 Start the Server

```bash
# Use the new refactored version
python app_refactored.py
```

You should see:
```
🚀 Starting LineUp API (Refactored) on port 5000
✅ Gemini API configured
✅ Virtual try-on configured
📊 Configuration: {...}
 * Running on http://0.0.0.0:5000
```

---

## 🌐 Open in Browser

Visit: **http://localhost:5000**

You should see:
- ✅ API information page with status
- ✅ List of available endpoints
- ✅ Configuration status

### Test the Frontend:

Open `index.html` in your browser or use a local server:
```bash
# Option 1: Python HTTP server
python -m http.server 8000
# Visit: http://localhost:8000

# Option 2: Just open the file
open index.html  # macOS
xdg-open index.html  # Linux
start index.html  # Windows
```

---

## ✅ Verify Everything Works

### 1. Check API Status:
```bash
curl http://localhost:5000/health
```

Should return:
```json
{
  "status": "healthy",
  "configuration": {
    "gemini_configured": true,
    ...
  }
}
```

### 2. Run Tests:
```bash
pytest -v
```

Should see:
```
tests/test_api.py::test_index PASSED
tests/test_api.py::test_health PASSED
...
========== 30 passed in 2.5s ==========
```

### 3. Try the API:

**Get barbers:**
```bash
curl "http://localhost:5000/barbers?location=Atlanta,GA"
```

**Create appointment:**
```bash
curl -X POST http://localhost:5000/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "John Doe",
    "barber_name": "Best Cuts",
    "barber_id": "barber_1",
    "date": "2025-12-31",
    "time": "14:00",
    "service": "Haircut"
  }'
```

---

## 📱 Install as PWA (Progressive Web App)

### On Mobile:

**iOS (Safari):**
1. Open app in Safari
2. Tap Share button (square with arrow)
3. Scroll and tap "Add to Home Screen"
4. Tap "Add"

**Android (Chrome):**
1. Open app in Chrome
2. Tap three dots menu
3. Tap "Install app" or "Add to Home screen"

### On Desktop:

**Chrome/Edge:**
1. Look for install icon (⊕) in address bar
2. Click it
3. Click "Install"

The app now works offline and loads faster!

---

## 🧪 Development Workflow

### Making Changes:

```bash
# 1. Edit code
nano services.py  # or use your editor

# 2. Run tests to verify
pytest

# 3. Format code (optional)
black .

# 4. Check for issues
flake8 .

# 5. Restart server
python app_refactored.py
```

### Database Management:

```bash
# View database
sqlite3 lineup.db
> .tables
> SELECT * FROM appointments;
> .exit

# Reset database
rm lineup.db
python app_refactored.py  # Will recreate
```

---

## 🎨 What to Try First

### 1. AI Hair Analysis
1. Upload a photo in the UI
2. Click "Analyze my look"
3. See AI-powered haircut recommendations
4. Try "Preview Style" buttons

### 2. Find Barbers
1. Go to "Explore" tab
2. Enter your location
3. See real barbershops near you
4. Book an appointment

### 3. Social Feed
1. Go to "Community" tab
2. Click "+ Post"
3. Share a haircut photo
4. Like other posts

### 4. Barber Mode
1. Click "Barber" button in header
2. View your dashboard
3. Upload portfolio photos
4. Manage appointments

---

## 🐛 Troubleshooting

### Port already in use:
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
PORT=8000 python app_refactored.py
```

### Module not found:
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Database errors:
```bash
# Delete and recreate
rm lineup.db
python app_refactored.py
```

### Tests failing:
```bash
# Make sure you're in the right directory
cd /path/to/LineUp-2
pytest
```

### API returns mock data:
- Check .env file has GEMINI_API_KEY
- Verify API key is valid
- Check server logs for errors

---

## 📊 Performance Tips

### For Development:
- SQLite is perfect (no setup needed)
- Memory cache works fine
- Mock data is fast for testing

### For Production:
- Use PostgreSQL (free: Render.com, Supabase)
- Add Redis (free: Upstash, Redis Labs)
- Enable caching in .env

---

## 🎓 Learn More

**Full Documentation:**
- `README_IMPROVEMENTS.md` - Complete feature guide
- `HAIRFAST_SETUP.md` - Virtual try-on setup
- `env.example.txt` - All configuration options

**Test Examples:**
- `tests/test_api.py` - See how to use the API

**Code Examples:**
- `services.py` - Business logic patterns
- `models.py` - Data validation examples
- `utils.js` - Frontend utilities

---

## 💡 Pro Tips

1. **Start minimal:** Just GEMINI_API_KEY is enough to try everything
2. **Use SQLite:** It's fast and needs zero setup
3. **Install as PWA:** Works like a native app
4. **Run tests often:** Catch bugs early
5. **Check logs:** Helpful for debugging

---

## 🎉 You're Ready!

```bash
# Start building!
python app_refactored.py

# Open browser
open http://localhost:5000
```

**Questions?** Check:
- Server logs in terminal
- Browser console (F12)
- Test output: `pytest -v`
- README_IMPROVEMENTS.md

**Happy coding! 🚀**

