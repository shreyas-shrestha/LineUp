# Replicate Integration - Quick Start

## TL;DR

Replicate is **already integrated**. Just add your API token.

## 3-Step Setup

### 1. Get Token
- Visit: https://replicate.com/account/api-tokens
- Create token (starts with `r8_...`)

### 2. Add to Environment
**Local (.env file)**:
```bash
REPLICATE_API_TOKEN=r8_your_token_here
```

**Render (Dashboard)**:
- Environment → Add `REPLICATE_API_TOKEN` → Paste token → Save

### 3. Test
- Upload photo in app
- Click "Try On" any style
- Check backend logs for: `"Using Replicate API"`

## How It Works

The app automatically tries in this order:
1. **HairFastGAN** (free, if HF_TOKEN set)
2. **Replicate** (paid, if REPLICATE_API_TOKEN set) ← **You are here**
3. **Preview Mode** (always works as fallback)

## Current Model

- **Model**: `cjwbw/style-your-hair`
- **Input**: User photo + reference hairstyle image
- **Output**: AI-transformed image
- **Cost**: ~$0.02-0.05 per transformation
- **Speed**: 10-30 seconds

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Replicate not installed" | `pip install replicate==0.22.0` |
| "401 Unauthorized" | Check API token is correct |
| "402 Payment Required" | Add credits to Replicate account |
| Slow response | Normal (10-30 sec), use loading state |

## Cost Estimates

- 100 transformations/day = ~$60-150/month
- 1,000 transformations/day = ~$600-1,500/month

## Full Documentation

See `REPLICATE_INTEGRATION_GUIDE.md` for complete details.


