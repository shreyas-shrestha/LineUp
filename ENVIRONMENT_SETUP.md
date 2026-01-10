# Environment Setup

Use this checklist to configure LineUp for production deployments. Copy these
variables into your hosting provider or a local `.env` file (if you maintain one
outside the repo).

## Required Keys

- `GEMINI_API_KEY` – Google Gemini model key for AI analysis.
- `GOOGLE_PLACES_API_KEY` – Google Places API key for real barber data.

## Optional but Recommended

- `REPLICATE_API_TOKEN` – Enables higher fidelity virtual try-on results.
- `HF_TOKEN` – Access token for HairFastGAN fallback.
- `FIREBASE_CREDENTIALS` – JSON from a Firebase service account for persistent
  storage (otherwise in-memory mocks are used).
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` –
  Allows uploading/barber portfolio assets without bloating responses.

## Runtime Controls

- `PORT` – HTTP port for Flask (defaults to 5000).
- `LINEUP_ALLOWED_ORIGINS` – Comma-separated list for production CORS (defaults
  to `https://lineupai.onrender.com,http://localhost:*`).

## Rate Limit Overrides

These accept any [Flask-Limiter](https://flask-limiter.readthedocs.io/) string:

- `LINEUP_GLOBAL_RATE`
- `LINEUP_APPOINTMENT_RATE`
- `LINEUP_APPOINTMENT_STATUS_RATE`
- `LINEUP_APPOINTMENTS_LIST_RATE`
- `LINEUP_PLACES_RATE`
- `LINEUP_AI_RATE`
- `LINEUP_TRYON_RATE`
- `LINEUP_SOCIAL_RATE`
- `LINEUP_SOCIAL_READ_RATE`

