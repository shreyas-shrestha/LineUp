# 🚀 Deployment Guide - LineUp AI

Complete guide to deploying LineUp AI to production using **FREE hosting services**.

---

## 🎯 Deployment Options (All FREE)

### Option 1: Render.com (Recommended)
- ✅ Free PostgreSQL database
- ✅ Free web service (750 hours/month)
- ✅ Auto-deploy from GitHub
- ✅ Environment variables in dashboard
- ✅ Built-in SSL

### Option 2: Railway.app
- ✅ $5 free credit monthly
- ✅ Easy deployment
- ✅ PostgreSQL included
- ✅ Auto-scaling

### Option 3: Fly.io
- ✅ Free tier for hobby projects
- ✅ Global edge deployment
- ✅ PostgreSQL included

---

## 📦 Option 1: Render.com Deployment (Easiest)

### Step 1: Prepare Your Repository

1. **Push to GitHub:**
```bash
git init
git add .
git commit -m "LineUp AI v2.0 - Production ready"
git branch -M main
git remote add origin https://github.com/yourusername/lineup-ai.git
git push -u origin main
```

2. **Ensure these files exist:**
- ✅ `requirements.txt`
- ✅ `app_refactored.py`
- ✅ `Procfile` (should contain: `web: gunicorn app_refactored:app`)

### Step 2: Create Render Account

1. Visit https://render.com
2. Sign up with GitHub
3. Authorize Render to access your repositories

### Step 3: Create PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Name: `lineup-db`
3. Database: `lineup`
4. User: `lineup_user`
5. Region: Choose closest to you
6. Plan: **Free**
7. Click "Create Database"
8. **Copy the Internal Database URL** (you'll need this)

### Step 4: Create Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name:** `lineup-ai`
   - **Region:** Same as database
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app_refactored:app --bind 0.0.0.0:$PORT`
   - **Plan:** Free

### Step 5: Set Environment Variables

In Render dashboard, add these environment variables:

```
# Required
DATABASE_URL=<paste the Internal Database URL from Step 3>
SECRET_KEY=<generate a random string>
GEMINI_API_KEY=<your Gemini API key>

# Optional but recommended
GOOGLE_PLACES_API_KEY=<your Places API key>
MODAL_HAIRFAST_ENDPOINT=<your Modal endpoint>

# Configuration
PORT=10000
DEBUG=False
CORS_ORIGINS=https://yourapp.onrender.com,*
```

**Generate SECRET_KEY:**
```bash
python -c "import os; print(os.urandom(24).hex())"
```

### Step 6: Deploy

1. Click "Create Web Service"
2. Wait 2-3 minutes for deployment
3. Visit your app at: `https://yourapp.onrender.com`

### Step 7: Deploy Frontend

**Option A: Same Render service (static files)**
- Add `index.html` to your repository
- Render will serve it automatically

**Option B: Vercel (recommended for frontend)**
1. Visit https://vercel.com
2. Import your repository
3. Deploy `index.html`
4. Update `API_URL` in `scripts-updated.js` to point to your Render backend

---

## 📦 Option 2: Railway.app Deployment

### Quick Deploy

1. Visit https://railway.app
2. Sign up with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository
6. Railway auto-detects Python and deploys!

### Configuration

Add environment variables in Railway dashboard:
```
GEMINI_API_KEY=<your key>
DATABASE_URL=postgresql://...  # Auto-provided by Railway
SECRET_KEY=<random string>
```

Railway automatically:
- ✅ Detects Python
- ✅ Installs requirements.txt
- ✅ Runs your app
- ✅ Provides PostgreSQL
- ✅ Sets up HTTPS

---

## 📦 Option 3: Fly.io Deployment

### Install Fly CLI
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
iwr https://fly.io/install.ps1 -useb | iex
```

### Deploy
```bash
# Login
flyctl auth login

# Initialize
flyctl launch

# Deploy
flyctl deploy
```

Fly.io auto-configures:
- ✅ Dockerfile generation
- ✅ PostgreSQL cluster
- ✅ Environment variables
- ✅ Global CDN

---

## 🗄️ Database Options (FREE)

### Option 1: Render PostgreSQL (Recommended)
- **Free tier:** 1GB storage, 90-day data retention
- **Setup:** Automatic with Render
- **URL:** Provided in dashboard

### Option 2: Supabase
- **Free tier:** 500MB database, 2GB bandwidth
- **Setup:** 
  1. Visit https://supabase.com
  2. Create project
  3. Get connection string
  4. Add to DATABASE_URL

### Option 3: ElephantSQL
- **Free tier:** 20MB storage
- **Setup:**
  1. Visit https://elephantsql.com
  2. Create instance
  3. Copy URL to DATABASE_URL

### Option 4: Keep SQLite (Simple Projects)
```python
# In .env for production
DATABASE_URL=sqlite:///lineup.db

# Note: SQLite works but has limitations:
# - Single file (no concurrent writes)
# - Not distributed
# - Fine for <100 users
```

---

## 📝 Environment Variables Reference

### Required for Production:
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Security
SECRET_KEY=your-long-random-string-here

# AI Services
GEMINI_API_KEY=your-gemini-key

# Server
PORT=10000
DEBUG=False
```

### Optional but Recommended:
```bash
# Barber Discovery
GOOGLE_PLACES_API_KEY=your-places-key

# Virtual Try-On
MODAL_HAIRFAST_ENDPOINT=https://your-modal-endpoint.com

# Caching (improves performance)
REDIS_URL=redis://user:pass@host:port

# CORS
CORS_ORIGINS=https://yourfrontend.com,https://api.yourdomain.com
```

---

## 🔐 Security Checklist

Before deploying to production:

- [ ] Set DEBUG=False
- [ ] Use strong SECRET_KEY (not "dev-secret")
- [ ] Set proper CORS_ORIGINS (not "*")
- [ ] Use HTTPS (automatic on Render/Vercel/Railway)
- [ ] Secure environment variables (never commit .env)
- [ ] Use PostgreSQL (not SQLite for production)
- [ ] Enable rate limiting (already configured)
- [ ] Review API key quotas

---

## 🚀 Frontend Deployment

### Option 1: Vercel (Recommended)

1. Visit https://vercel.com
2. Import GitHub repository
3. Configure:
   - **Framework:** None (static)
   - **Root Directory:** `/`
   - **Build Command:** (leave empty)
   - **Output Directory:** (leave empty)
4. Deploy!

**Update API URL:**
```javascript
// In scripts-updated.js
const API_URL = 'https://your-backend.onrender.com';
```

### Option 2: Netlify

1. Visit https://netlify.com
2. Drag and drop your folder
3. Or connect GitHub for auto-deploy
4. Update API_URL in JavaScript

### Option 3: GitHub Pages

```bash
# Create gh-pages branch
git checkout -b gh-pages
git push origin gh-pages

# Enable in repository settings
# Visit: https://yourusername.github.io/lineup-ai
```

---

## 📊 Post-Deployment Checklist

After deploying:

- [ ] Test all features
  - [ ] AI analysis works
  - [ ] Barber search works
  - [ ] Appointments work
  - [ ] Social feed works
  - [ ] PWA installs

- [ ] Monitor
  - [ ] Check Render logs
  - [ ] Verify database connected
  - [ ] Test API endpoints
  - [ ] Check error rates

- [ ] Optimize
  - [ ] Enable Redis if needed
  - [ ] Set up monitoring (free: uptimerobot.com)
  - [ ] Configure backups

---

## 🔧 Troubleshooting

### Build Failed

**Problem:** Dependencies won't install
```bash
# Solution: Check requirements.txt
pip install -r requirements.txt  # Test locally
```

**Problem:** Port binding error
```bash
# Solution: Use $PORT environment variable
# In app_refactored.py:
port = int(os.environ.get('PORT', 5000))
```

### Runtime Errors

**Problem:** Database connection failed
```bash
# Check DATABASE_URL is set correctly
# For Render: Use Internal Database URL, not External
```

**Problem:** Module not found
```bash
# Ensure all files are committed
git status
git add .
git commit -m "Add missing files"
git push
```

### Performance Issues

**Problem:** Slow response times
```bash
# Add Redis:
# 1. Create Redis instance on Upstash (free)
# 2. Add REDIS_URL to environment
# 3. Restart service
```

**Problem:** Free tier sleep
```bash
# Render free tier sleeps after 15 min inactivity
# Solutions:
# 1. Upgrade to paid tier ($7/mo)
# 2. Use uptimerobot.com to ping every 5 min (free)
# 3. Accept the sleep (wakes in <30 seconds)
```

---

## 💰 Cost Breakdown

### Free Forever Setup:
```
Render Web Service:    $0 (750 hours/month)
Render PostgreSQL:     $0 (1GB storage)
Vercel Frontend:       $0 (100GB bandwidth)
Google Gemini:         $0 (60 req/min)
Google Places:         $0 ($200 monthly credit)
Modal Labs:            $0 ($30 monthly credit)
Total:                 $0/month ✅
```

### When You Need to Upgrade:
```
Render always-on:      $7/month (no sleep)
PostgreSQL 10GB:       $15/month
Vercel Pro:            $20/month (team features)
Redis 250MB:           $5/month
Total with upgrades:   $47/month
```

**Most apps never need upgrades!**

---

## 📈 Scaling Strategy

### Tier 1: Start (0-100 users) - FREE
- Render free tier
- SQLite or free PostgreSQL
- Memory caching
- **Cost: $0/month**

### Tier 2: Growing (100-1000 users) - CHEAP
- Render paid ($7/mo always-on)
- PostgreSQL 10GB ($15/mo)
- Redis cache ($5/mo)
- **Cost: $27/month**

### Tier 3: Scaling (1000+ users) - MODERATE
- Render Pro ($25/mo)
- PostgreSQL 100GB ($65/mo)
- Redis Pro ($10/mo)
- CDN (Cloudflare free)
- **Cost: $100/month**

---

## 🎯 Deployment Best Practices

1. **Use Git Tags**
```bash
git tag -a v2.0 -m "Version 2.0 release"
git push origin v2.0
```

2. **Enable Auto-Deploy**
- Connect GitHub to Render
- Push to main → auto-deploys

3. **Monitor Logs**
```bash
# Render dashboard → Logs tab
# Or use CLI:
render logs -f
```

4. **Set Up Alerts**
- Render: Email alerts for downtime
- UptimeRobot: Ping monitoring (free)
- Sentry: Error tracking (free tier)

5. **Database Backups**
- Render: Automatic backups
- Or: Setup cron job for manual backups

---

## 🔄 Update Strategy

### Rolling Updates (Zero Downtime):

1. **Test Locally**
```bash
git checkout -b feature/new-feature
# Make changes
pytest  # Test
git commit -m "Add new feature"
```

2. **Merge to Main**
```bash
git checkout main
git merge feature/new-feature
git push origin main
```

3. **Auto-Deploy**
- Render detects push
- Builds new version
- Deploys with zero downtime

---

## 📞 Support & Monitoring

### Free Monitoring Tools:

1. **UptimeRobot** (uptimerobot.com)
   - Ping every 5 minutes
   - Email alerts
   - 50 monitors free

2. **Sentry** (sentry.io)
   - Error tracking
   - Stack traces
   - 5k events/month free

3. **Google Analytics**
   - Usage analytics
   - Free forever

### Health Checks:

Your app includes a health endpoint:
```bash
curl https://yourapp.onrender.com/health
```

Set UptimeRobot to ping this every 5 minutes.

---

## ✅ Pre-Launch Checklist

- [ ] All tests passing locally
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] API keys valid and tested
- [ ] Frontend points to production API
- [ ] CORS configured correctly
- [ ] Rate limiting enabled
- [ ] Error handling tested
- [ ] Performance tested
- [ ] Security reviewed
- [ ] Backup strategy in place
- [ ] Monitoring configured

---

## 🎉 Launch!

Your LineUp AI app is now live at:
- Backend: `https://yourapp.onrender.com`
- Frontend: `https://yourapp.vercel.app`
- Database: Secured and backed up
- Monitoring: Active
- **Cost: $0/month**

**Congratulations! 🚀**

---

## 📚 Additional Resources

- [Render Docs](https://render.com/docs)
- [Railway Docs](https://docs.railway.app)
- [Vercel Docs](https://vercel.com/docs)
- [PostgreSQL Tips](https://www.postgresql.org/docs/)
- [Flask Production Guide](https://flask.palletsprojects.com/en/latest/deploying/)

---

*Happy Deploying! 🌟*

