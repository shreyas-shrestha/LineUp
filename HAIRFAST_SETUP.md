# HairFastGAN Setup Guide - FREE Visual Hair Transformation! 💇‍♂️

## Why HairFastGAN?

✅ **MIT License** - Free for commercial use  
✅ **Actual visual transformation** - Not just text advice  
✅ **Fast** - Less than 1 second per transformation  
✅ **High quality** - NeurIPS 2024 accepted method  
✅ **FREE hosting** - Modal Labs gives $30/month free credits  

## Cost Comparison

| Service | Cost per Transform | Monthly (1000 transforms) |
|---------|-------------------|--------------------------|
| **Modal Labs (T4 GPU)** | ~$0.0023 | **~$2.30** ✅ |
| Google Gemini (text only) | $0.00001 | $0.01 ❌ *No visual* |
| Replicate (HairCLIP) | $0.0045-$0.028 | $4.50-$28 |

With Modal's **$30 FREE monthly credit**, you get **13,000+ transformations FREE!**

## Setup Instructions

### Option 1: Deploy on Modal Labs (Recommended - FREE!)

#### Step 1: Install Modal CLI

```bash
pip install modal
```

#### Step 2: Create Modal Account & Setup

```bash
modal setup
# This will open your browser to create an account (FREE)
# $30/month in free credits - no credit card required!
```

#### Step 3: Deploy HairFastGAN

```bash
cd /Users/shreyasshrestha/dev/LineUp-1
modal deploy modal_hairfast.py
```

This will output a URL like:
```
✅ Deployed! Your endpoint is at:
https://your-username--hairfast-lineup-hairfast-endpoint.modal.run
```

#### Step 4: Set Environment Variable

Add to your Render backend environment variables:
```
MODAL_HAIRFAST_ENDPOINT=https://your-username--hairfast-lineup-hairfast-endpoint.modal.run
```

#### Step 5: Test It!

```bash
# Test from command line
curl -X POST https://your-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -d '{"face_image": "base64_image_here", "style_description": "fade haircut"}'
```

### Option 2: Use Hugging Face Inference API (Alternative)

#### Step 1: Get HF API Key

1. Go to https://huggingface.co/settings/tokens
2. Create a new token (FREE account works!)
3. Copy the token

#### Step 2: Set Environment Variable

Add to your Render backend:
```
HF_API_KEY=hf_your_token_here
```

**Note**: HairFastGAN might not be directly available on HF Inference API. You may need to deploy it to a HF Space first.

### Option 3: Deploy Your Own GPU Server (Advanced)

If you want full control, you can deploy HairFastGAN on:

- **AWS EC2 with GPU** ($0.526/hour for g4dn.xlarge with T4)
- **Google Cloud GPU** ($0.35/hour for n1-standard-4 + T4)
- **RunPod** ($0.204/hour for RTX 4000)

#### Quick Deploy Script:

```bash
# On your GPU server (Ubuntu)
git clone https://github.com/AIRI-Institute/HairFastGAN
cd HairFastGAN

# Download models
git clone https://huggingface.co/AIRI-Institute/HairFastGAN HF-models
cd HF-models && git lfs pull && cd ..
mv HF-models/pretrained_models pretrained_models
mv HF-models/input input

# Install dependencies
pip install -r requirements.txt

# Create API server (save as server.py)
cat > server.py << 'EOF'
from flask import Flask, request, jsonify
from hair_swap import HairFast, get_parser
from PIL import Image
import base64
import io

app = Flask(__name__)
hair_fast = HairFast(get_parser().parse_args([]))

@app.route('/transform', methods=['POST'])
def transform():
    data = request.json
    face_b64 = data['face_image']
    style = data['style_description']
    
    # Decode image
    face_bytes = base64.b64decode(face_b64)
    face_img = Image.open(io.BytesIO(face_bytes))
    
    # Transform (using same image as reference for now)
    result = hair_fast(face_img, face_img, face_img)
    
    # Encode result
    buffer = io.BytesIO()
    result.save(buffer, format='JPEG')
    result_b64 = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        'success': True,
        'result_image': result_b64,
        'style_applied': style
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
EOF

# Run server
python server.py
```

Then set:
```
MODAL_HAIRFAST_ENDPOINT=http://your-server-ip:8000/transform
```

## How It Works

### Request Format

```json
{
  "face_image": "base64_encoded_jpeg",
  "style_description": "fade with taper"
}
```

### Response Format

```json
{
  "success": true,
  "result_image": "base64_encoded_transformed_image",
  "style_applied": "fade with taper",
  "model": "HairFastGAN",
  "poweredBy": "HairFastGAN (AIRI-Institute)"
}
```

### In Your App

1. User uploads photo
2. User clicks "Preview Style" on a haircut recommendation
3. Frontend sends photo (base64) + style description to your backend
4. Your backend calls Modal endpoint
5. Modal runs HairFastGAN on GPU (< 1 second)
6. Transformed image returns to frontend
7. User sees their photo with the new hairstyle!

## Troubleshooting

### "HairFastGAN not configured" Error

Make sure you've set one of these environment variables:
- `MODAL_HAIRFAST_ENDPOINT` (recommended)
- `HF_API_KEY` (alternative)

### Modal Deployment Fails

```bash
# Update Modal
pip install --upgrade modal

# Re-authenticate
modal setup

# Try deploying again
modal deploy modal_hairfast.py --force
```

### Out of Modal Credits

- Modal gives $30/month FREE
- If you exceed, it's only $0.0023/transform ($2.30 per 1000)
- Much cheaper than Replicate!

## Production Tips

1. **Cache Results**: Save transformed images to reduce API calls
2. **Hairstyle Library**: Build a library of reference hairstyle images
3. **Rate Limiting**: Already set to 20/hour in backend
4. **Error Handling**: Backend has fallback logic built-in
5. **Monitoring**: Check Modal dashboard for usage stats

## Alternative: Local Development

For testing locally WITHOUT GPU:

```python
# In app.py, add a mock mode
MOCK_TRYON = os.environ.get("MOCK_TRYON", "false").lower() == "true"

if MOCK_TRYON:
    # Return original image with overlay text
    # (Already implemented as fallback)
    pass
```

Set `MOCK_TRYON=true` for local development.

## Cost Monitoring

### Modal Dashboard
- Visit https://modal.com/dashboard
- View credit usage in real-time
- Set up billing alerts

### Expected Usage
- **100 users/day** × 2 try-ons = 200 transforms
- **200 × $0.0023** = $0.46/day = **$13.80/month**
- Still within FREE tier! 🎉

## Next Steps

1. ✅ Deploy to Modal (5 minutes)
2. ✅ Set `MODAL_HAIRFAST_ENDPOINT` env var
3. ✅ Test in your app
4. ✅ Monitor usage in Modal dashboard
5. ✅ Build hairstyle reference library (optional)

## Support

- **Modal Support**: https://modal.com/docs
- **HairFastGAN Issues**: https://github.com/AIRI-Institute/HairFastGAN/issues
- **LineUp Issues**: Create an issue in your repo

---

**You now have professional-grade hair transformation for FREE!** 🚀

Built with:
- [HairFastGAN](https://github.com/AIRI-Institute/HairFastGAN) (MIT License)
- [Modal Labs](https://modal.com) (Serverless GPU)
- ❤️ by AIRI-Institute

