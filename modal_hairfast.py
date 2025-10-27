"""
Modal Labs deployment for HairFastGAN
======================================
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
        "requests"  # For downloading reference hairstyle images
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
    timeout=300,
    memory=8192
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
    import sys
    sys.path.append("/root/HairFastGAN")
    
    from PIL import Image
    from hair_swap import HairFast, get_parser
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    try:
        logger.info(f"Starting transformation for style: {style_description}")
        
        # Decode input image
        face_bytes = base64.b64decode(face_image_base64)
        face_img = Image.open(io.BytesIO(face_bytes)).convert('RGB')
        logger.info(f"Face image loaded: {face_img.size}")
        
        # HairFastGAN requires reference images for shape and color
        # Map style descriptions to reference hairstyle URLs
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
            "ivy league": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop"
        }
        
        # Find matching hairstyle reference
        style_lower = style_description.lower()
        reference_url = None
        
        for key, url in hairstyle_library.items():
            if key in style_lower:
                reference_url = url
                logger.info(f"Matched style '{key}' for '{style_description}'")
                break
        
        # Default to a classic style if no match
        if not reference_url:
            reference_url = hairstyle_library["side part"]
            logger.warning(f"No match for '{style_description}', using default: side part")
        
        # Download reference image
        logger.info(f"Downloading reference from: {reference_url}")
        ref_response = requests.get(reference_url, timeout=10)
        if ref_response.status_code != 200:
            raise Exception(f"Failed to download reference image: HTTP {ref_response.status_code}")
        
        ref_img = Image.open(io.BytesIO(ref_response.content)).convert('RGB')
        logger.info(f"Reference image loaded: {ref_img.size}")
        
        # Initialize HairFast
        logger.info("Initializing HairFastGAN...")
        args = get_parser().parse_args([])
        hair_fast = HairFast(args)
        
        # Transform: face image + reference hairstyle shape + reference hair color
        logger.info("Running HairFastGAN transformation...")
        result = hair_fast(face_img, ref_img, ref_img)
        logger.info(f"Transformation complete! Result size: {result.size}")
        
        # Convert result to base64
        output_buffer = io.BytesIO()
        result.save(output_buffer, format='JPEG', quality=95)
        result_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "result_image": result_base64,
            "style_applied": style_description,
            "model": "HairFastGAN",
            "gpu_used": "NVIDIA T4",
            "reference_used": reference_url
        }
        
    except Exception as e:
        logger.error(f"Transformation failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

# Create web endpoint
@app.function(image=hairfast_image)
@modal.fastapi_endpoint(method="POST")
def hairfast_endpoint(request_data: dict) -> dict:
    """
    Web endpoint for HairFastGAN transformations
    
    POST request body:
    {
        "face_image": "base64_encoded_image",
        "style_description": "fade with taper"
    }
    """
    face_image = request_data.get("face_image", "")
    style_description = request_data.get("style_description", "")
    
    if not face_image or not style_description:
        return {
            "success": False,
            "error": "Missing required fields: face_image and style_description"
        }
    
    # Call the GPU function
    result = transform_hair.remote(face_image, style_description)
    return result

# Local testing function
@app.local_entrypoint()
def test():
    """Test the deployment locally"""
    print("🚀 Testing HairFastGAN deployment...")
    
    # Create a test image
    from PIL import Image
    import io
    
    test_img = Image.new('RGB', (512, 512), color='white')
    buffer = io.BytesIO()
    test_img.save(buffer, format='JPEG')
    test_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    result = transform_hair.remote(test_base64, "fade haircut")
    print(f"✅ Result: {result.get('success')}")
    print(f"📊 Model: {result.get('model')}")
    print(f"💻 GPU: {result.get('gpu_used')}")

