"""
Modal Labs deployment for HairFastGAN - FIXED VERSION
======================================================
This script deploys HairFastGAN on Modal's serverless GPU platform.

FREE TIER: Modal provides $30/month free credits - enough for 1000+ transformations!

Setup:
1. Install Modal: pip install modal
2. Create account: modal setup
3. Deploy: modal deploy modal_hairfast.py
4. Get endpoint URL and set as MODAL_HAIRFAST_ENDPOINT env var

MIT License - HairFastGAN by AIRI-Institute
https://github.com/AIRI-Institute/HairFastGAN
"""

import modal
import base64
import io
import sys
import traceback

# Create Modal app
app = modal.App("hairfast-lineup")

# Define the image with HairFastGAN dependencies
hairfast_image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "git-lfs", "libgl1-mesa-glx", "libglib2.0-0", "cmake", "build-essential")
    .pip_install(
        "numpy<2",  # Pin to 1.x for compatibility
        "torch==1.13.1",
        "torchvision==0.14.1",
        "pillow",
        "opencv-python-headless",
        "scipy",
        "ninja",
        "dlib",
        "face-alignment",
        "gdown",
        "fastapi",
        "requests",  # For downloading reference hairstyle images
        "addict",  # Required by HairFastGAN for nested dicts
        "yacs"  # Required by HairFastGAN for config management
    )
    .run_commands(
        # Clone HairFastGAN
        "cd /root && git clone https://github.com/AIRI-Institute/HairFastGAN",
        # Download pretrained models from Hugging Face
        "cd /root && git clone https://huggingface.co/AIRI-Institute/HairFastGAN HairFastGAN-models",
        "cd /root/HairFastGAN-models && git lfs pull",
        "mv /root/HairFastGAN-models/pretrained_models /root/HairFastGAN/",
        "mv /root/HairFastGAN-models/input /root/HairFastGAN/"
    )
)

# Create a Modal function with GPU
@app.function(
    image=hairfast_image,
    gpu="T4",  # FREE tier GPU!
    timeout=600,  # Increased timeout to 10 minutes
    memory=8192,
    keep_warm=1  # Keep one instance warm to avoid cold starts
)
def transform_hair(face_image_base64: str, style_description: str) -> dict:
    """
    Transform hair using HairFastGAN
    
    Args:
        face_image_base64: Base64 encoded face image
        style_description: Text description of desired hairstyle
    
    Returns:
        dict with result_image (base64) and metadata
    """
    import logging
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=" * 50)
        logger.info(f"🎨 STARTING TRANSFORMATION")
        logger.info(f"Style requested: {style_description}")
        logger.info(f"Image data size: {len(face_image_base64)} bytes")
        logger.info("=" * 50)
        
        # Add HairFastGAN to Python path
        sys.path.insert(0, "/root/HairFastGAN")
        logger.info("✅ Added HairFastGAN to path")
        
        # Import required modules
        from PIL import Image
        import requests
        
        logger.info("✅ Imported dependencies")
        
        # Validate base64 input
        if not face_image_base64:
            raise ValueError("Empty face_image_base64 provided")
        
        if len(face_image_base64) < 100:
            raise ValueError(f"face_image_base64 too short: {len(face_image_base64)} bytes")
        
        # Decode input image
        logger.info("📸 Decoding face image...")
        try:
            face_bytes = base64.b64decode(face_image_base64)
            logger.info(f"✅ Decoded {len(face_bytes)} bytes")
        except Exception as e:
            raise ValueError(f"Failed to decode base64: {str(e)}")
        
        try:
            face_img = Image.open(io.BytesIO(face_bytes)).convert('RGB')
            logger.info(f"✅ Face image loaded: {face_img.size}")
        except Exception as e:
            raise ValueError(f"Failed to open image: {str(e)}")
        
        # Resize if too large
        max_size = 1024
        if face_img.width > max_size or face_img.height > max_size:
            ratio = min(max_size / face_img.width, max_size / face_img.height)
            new_size = (int(face_img.width * ratio), int(face_img.height * ratio))
            face_img = face_img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"✅ Resized to: {face_img.size}")
        
        # Hairstyle reference library
        hairstyle_library = {
            "fade": "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=512&h=512&fit=crop",
            "buzz": "https://images.unsplash.com/photo-1564564321837-a57b7070ac4f?w=512&h=512&fit=crop",
            "quiff": "https://images.unsplash.com/photo-1605497788044-5a32c7078486?w=512&h=512&fit=crop",
            "pompadour": "https://images.unsplash.com/photo-1633681926022-84c23e8cb2d6?w=512&h=512&fit=crop",
            "undercut": "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=512&h=512&fit=crop",
            "side part": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop",
            "slick back": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=512&h=512&fit=crop",
            "long": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=512&h=512&fit=crop",
            "curly": "https://images.unsplash.com/photo-1524660988542-c440de9c0fde?w=512&h=512&fit=crop",
            "textured": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=512&h=512&fit=crop",
            "crew cut": "https://images.unsplash.com/photo-1564564321837-a57b7070ac4f?w=512&h=512&fit=crop",
            "classic": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop",
            "modern": "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=512&h=512&fit=crop"
        }
        
        # Find matching hairstyle reference
        style_lower = style_description.lower()
        reference_url = None
        matched_key = None
        
        for key, url in hairstyle_library.items():
            if key in style_lower:
                reference_url = url
                matched_key = key
                logger.info(f"✅ Matched style '{key}' for '{style_description}'")
                break
        
        # Default to side part if no match
        if not reference_url:
            reference_url = hairstyle_library["side part"]
            matched_key = "side part"
            logger.warning(f"⚠️ No match for '{style_description}', using default: {matched_key}")
        
        # Download reference image
        logger.info(f"📥 Downloading reference from: {reference_url}")
        try:
            ref_response = requests.get(reference_url, timeout=30)
            if ref_response.status_code != 200:
                raise Exception(f"HTTP {ref_response.status_code}")
            
            ref_img = Image.open(io.BytesIO(ref_response.content)).convert('RGB')
            logger.info(f"✅ Reference image loaded: {ref_img.size}")
        except Exception as e:
            raise Exception(f"Failed to download reference image: {str(e)}")
        
        # Initialize HairFast
        logger.info("🚀 Initializing HairFastGAN...")
        try:
            from hair_swap import HairFast, get_parser
            
            args = get_parser().parse_args([])
            hair_fast = HairFast(args)
            logger.info("✅ HairFastGAN initialized")
        except Exception as e:
            logger.error(f"Failed to initialize HairFastGAN: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"HairFastGAN initialization failed: {str(e)}")
        
        # Run transformation
        logger.info("✨ Running transformation...")
        try:
            result = hair_fast(face_img, ref_img, ref_img)
            logger.info(f"✅ Transformation complete! Result size: {result.size}")
        except Exception as e:
            logger.error(f"Transformation failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise Exception(f"HairFastGAN transformation failed: {str(e)}")
        
        # Convert result to base64
        logger.info("💾 Encoding result...")
        output_buffer = io.BytesIO()
        result.save(output_buffer, format='JPEG', quality=95)
        result_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        logger.info(f"✅ Result encoded: {len(result_base64)} bytes")
        
        logger.info("=" * 50)
        logger.info("🎉 TRANSFORMATION SUCCESSFUL")
        logger.info("=" * 50)
        
        return {
            "success": True,
            "result_image": result_base64,
            "style_applied": style_description,
            "matched_style": matched_key,
            "model": "HairFastGAN",
            "gpu_used": "NVIDIA T4",
            "reference_used": reference_url
        }
        
    except Exception as e:
        logger.error("=" * 50)
        logger.error("❌ TRANSFORMATION FAILED")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 50)
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

# Create web endpoint with better error handling
@app.function(
    image=hairfast_image,
    timeout=60
)
@modal.web_endpoint(method="POST")
async def hairfast_endpoint(request_data: dict) -> dict:
    """
    Web endpoint for HairFastGAN transformations
    
    POST request body:
    {
        "face_image": "base64_encoded_image",
        "style_description": "fade with taper"
    }
    """
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info("🌐 Endpoint called")
    
    try:
        # Validate request data
        if not isinstance(request_data, dict):
            return {
                "success": False,
                "error": "Request body must be a JSON object"
            }
        
        face_image = request_data.get("face_image", "")
        style_description = request_data.get("style_description", "")
        
        logger.info(f"Request: style='{style_description}', image_size={len(face_image)}")
        
        if not face_image:
            return {
                "success": False,
                "error": "Missing required field: face_image"
            }
        
        if not style_description:
            return {
                "success": False,
                "error": "Missing required field: style_description"
            }
        
        # Call the GPU function
        logger.info("🚀 Calling GPU function...")
        result = transform_hair.remote(face_image, style_description)
        
        logger.info(f"✅ GPU function returned: success={result.get('success')}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Endpoint error: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": f"Endpoint error: {str(e)}",
            "error_type": type(e).__name__
        }

# Local testing function
@app.local_entrypoint()
def test():
    """Test the deployment locally"""
    print("🚀 Testing HairFastGAN deployment...")
    print("=" * 50)
    
    # Create a test image
    from PIL import Image
    import io
    
    # Create a simple test image
    test_img = Image.new('RGB', (512, 512), color=(255, 200, 200))
    buffer = io.BytesIO()
    test_img.save(buffer, format='JPEG')
    test_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    print(f"📸 Test image size: {len(test_base64)} bytes")
    print("🎨 Testing transformation with 'fade haircut'...")
    print("=" * 50)
    
    result = transform_hair.remote(test_base64, "fade haircut")
    
    print("\n" + "=" * 50)
    print("📊 RESULTS:")
    print("=" * 50)
    print(f"✅ Success: {result.get('success')}")
    
    if result.get('success'):
        print(f"📊 Model: {result.get('model')}")
        print(f"💻 GPU: {result.get('gpu_used')}")
        print(f"🎨 Style: {result.get('style_applied')}")
        print(f"🔗 Reference: {result.get('reference_used')}")
        print(f"📦 Result size: {len(result.get('result_image', ''))} bytes")
    else:
        print(f"❌ Error: {result.get('error')}")
        print(f"📝 Error type: {result.get('error_type')}")
    
    print("=" * 50)
