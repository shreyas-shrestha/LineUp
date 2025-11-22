# Replicate Hair Try-On Integration Guide

## Overview

Replicate is already integrated into the LineUp app as **Tier 2** in the multi-tier fallback system:
1. **Tier 1**: HairFastGAN (free, Hugging Face)
2. **Tier 2**: Replicate (paid, more reliable) ← **You are here**
3. **Tier 3**: Preview Mode (always works, fallback)

## Current Implementation

The Replicate integration uses the `cjwbw/style-your-hair` model which performs real hair style transfer from a reference image to the user's photo.

**Model**: `cjwbw/style-your-hair:d28c54ed4e370318f03e2e7e763938e33cf8b2d9b4ac1ad42af0de78cb1e6ea3`

**Location in code**: `app.py` lines 1436-1595

## Setup Instructions

### Step 1: Get Replicate API Token

1. Go to https://replicate.com/signin
2. Sign up or log in (FREE account with credits)
3. Navigate to https://replicate.com/account/api-tokens
4. Click "Create token"
5. Copy the token (starts with `r8_...`)

### Step 2: Add to Environment Variables

**For Local Development:**
```bash
# Create or edit .env file in project root
REPLICATE_API_TOKEN=r8_your_token_here
```

**For Render Deployment:**
1. Go to your Render dashboard
2. Select your backend web service
3. Go to "Environment" tab
4. Add new variable:
   - **Key**: `REPLICATE_API_TOKEN`
   - **Value**: `r8_your_token_here` (paste your token)
5. Click "Save Changes"
6. Render will auto-redeploy (~2 minutes)

### Step 3: Verify Installation

Check that the `replicate` package is installed:

```bash
pip install replicate==0.22.0
```

It's already in `requirements.txt`, so running `pip install -r requirements.txt` will install it.

### Step 4: Test Integration

1. Start your backend: `python app.py`
2. Check logs for: `"Replicate library loaded successfully"`
3. Make a virtual try-on request
4. Check logs for: `"Using Replicate API for REAL hair style transformation"`

## How It Works

### Current Flow

```
User uploads photo + selects style
    ↓
POST /virtual-tryon
    ↓
Tier 1: Try HairFastGAN (if HF_TOKEN exists)
    ↓ (if fails or no token)
Tier 2: Try Replicate (if REPLICATE_API_TOKEN exists) ← **You are here**
    ↓ (if fails)
Tier 3: Preview Mode (always works)
```

### What the Code Does

1. **Checks for API Token**: Verifies `REPLICATE_API_TOKEN` environment variable exists
2. **Converts Image**: Transforms base64 to data URI format
3. **Maps Style Description**: Matches user's style choice to a detailed prompt
4. **Selects Reference Image**: Chooses a high-quality reference hairstyle image from Unsplash
5. **Calls Replicate API**: Sends face image + reference style image to the model
6. **Downloads Result**: Fetches the transformed image from Replicate's CDN
7. **Returns Base64**: Converts result to base64 for frontend display

### Model Parameters

```python
replicate.run(
    "cjwbw/style-your-hair:d28c54ed4e370318f03e2e7e763938e33cf8b2d9b4ac1ad42af0de78cb1e6ea3",
    input={
        "face_image": face_data_uri,      # User's photo (data URI)
        "style_image": reference_url,      # Reference hairstyle (URL)
        "color_transfer": "True"           # Transfer hair color too
    }
)
```

## Supported Styles

The integration supports these hairstyles with automatic matching:

- fade
- buzz
- quiff
- pompadour
- undercut
- side part
- slick back
- long
- curly
- textured
- mohawk
- crew cut
- bowl cut
- man bun
- dreadlocks
- afro

**Note**: The code uses keyword matching, so "modern fade" will match "fade", "buzz cut" will match "buzz", etc.

## Pricing

### Replicate Pricing Model

- **Free Credits**: New accounts get free credits to test
- **Pay Per Use**: ~$0.02-0.05 per image transformation
- **Example Costs**:
  - 100 transformations/day = ~$60-150/month
  - 1,000 transformations/day = ~$600-1,500/month

### Cost Optimization Tips

1. **Use Preview Mode for Free Users**: Only use Replicate for premium users
2. **Cache Results**: Store common style transformations
3. **Rate Limiting**: Already implemented (20 req/hour)
4. **Fallback Strategy**: Falls back to preview mode if Replicate fails

## Troubleshooting

### Issue: "Replicate not installed"

**Solution**: 
```bash
pip install replicate==0.22.0
```

### Issue: "Replicate hair style transfer error"

**Check**:
1. API token is set correctly
2. Token has not expired
3. Account has credits/quota available
4. Check logs for specific error message

**Common Errors**:
- `401 Unauthorized` → Invalid or missing API token
- `429 Too Many Requests` → Rate limit exceeded
- `402 Payment Required` → Out of credits
- `500 Internal Server Error` → Model error (try again)

### Issue: Output is not an image

**Check**:
- Image format is supported (JPEG, PNG)
- Base64 encoding is correct
- Reference image URL is accessible

### Issue: Slow response times

**Normal**: Replicate transformations take 10-30 seconds
**Optimization**: 
- Use async processing with background jobs
- Show loading state in frontend
- Consider caching popular transformations

## Code Improvements

### Potential Enhancements

1. **Better Style Matching**
   ```python
   # Current: Simple keyword matching
   # Improvement: Use fuzzy string matching or ML classification
   from fuzzywuzzy import fuzz
   best_match = max(style_prompts.keys(), 
                    key=lambda x: fuzz.ratio(style_lower, x))
   ```

2. **Async Processing**
   ```python
   # Current: Synchronous (blocks request)
   # Improvement: Use background jobs (Celery, Redis Queue)
   # Return job ID immediately, poll for results
   ```

3. **Result Caching**
   ```python
   # Cache transformations by (photo_hash, style)
   # Avoid duplicate API calls
   cache_key = f"{photo_hash}_{style_description}"
   if cache_key in transformation_cache:
       return cache[cache_key]
   ```

4. **Better Error Messages**
   ```python
   # More specific error handling
   if "quota" in str(e).lower():
       return "Out of Replicate credits"
   elif "timeout" in str(e).lower():
       return "Transformation timed out, please try again"
   ```

5. **Progress Updates**
   ```python
   # Use Replicate's webhook or polling for progress
   # Update frontend in real-time
   prediction = replicate.predictions.create(...)
   while prediction.status == "starting":
       prediction.reload()
       # Send progress update
   ```

## Testing the Integration

### Manual Test

```bash
# Test endpoint directly
curl -X POST http://localhost:5000/virtual-tryon \
  -H "Content-Type: application/json" \
  -d '{
    "userPhoto": "base64_image_data_here",
    "styleDescription": "fade"
  }'
```

### Expected Response

```json
{
  "success": true,
  "message": "✨ Real AI hair transformation complete: fade",
  "resultImage": "base64_encoded_image",
  "styleApplied": "fade",
  "poweredBy": "Replicate Style-Your-Hair AI",
  "note": "This is a real AI transformation!"
}
```

### Check Logs

Look for these log messages:
```
INFO: Using Replicate API for REAL hair style transformation
INFO: Starting hair style transformation: fade
INFO: Using prompt: short fade haircut with clean sides and textured top
INFO: Using reference image: https://images.unsplash.com/...
INFO: Replicate API called successfully
INFO: Downloading result from: https://replicate.delivery/...
INFO: ✅ AI hair transformation successful!
```

## Alternative Models

If `cjwbw/style-your-hair` doesn't work well, consider these alternatives:

### Option 1: flux-kontext-apps/change-haircut
```python
output = replicate.run(
    "flux-kontext-apps/change-haircut:latest",
    input={
        "image": face_data_uri,
        "haircut_style": style_description
    }
)
```

### Option 2: codefold/hair
```python
output = replicate.run(
    "codefold/hair:latest",
    input={
        "source_image": face_data_uri,
        "target_hairstyle": reference_url
    }
)
```

**To switch models**: Update line 1511 in `app.py` with the new model identifier.

## Security Considerations

1. **API Token Security**:
   - Never commit tokens to git
   - Use environment variables only
   - Rotate tokens regularly

2. **Image Privacy**:
   - Images sent to Replicate are processed on their servers
   - Review Replicate's privacy policy
   - Consider on-premise alternative for sensitive use cases

3. **Rate Limiting**:
   - Already implemented: 20 req/hour
   - Consider per-user limits for paid features

## Monitoring

### Key Metrics to Track

1. **Success Rate**: % of successful transformations
2. **Response Time**: Average time for transformation
3. **Error Rate**: % of failed attempts
4. **Cost per Transformation**: Track spending
5. **Usage Patterns**: Peak times, popular styles

### Add Logging

```python
# Track metrics
logger.info(f"Replicate transformation: style={style}, duration={duration}ms, cost=${cost}")
```

## Summary

Replicate is **already fully integrated** and ready to use. You just need to:

1. ✅ Get API token from Replicate
2. ✅ Add `REPLICATE_API_TOKEN` to environment variables
3. ✅ Deploy/restart backend
4. ✅ Test with a photo upload

The integration will automatically:
- Try HairFastGAN first (if configured)
- Fall back to Replicate if available
- Use Preview Mode if both fail

**No code changes needed** - it's all set up!


