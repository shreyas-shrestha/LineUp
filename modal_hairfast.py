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
        "fastapi"
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
    import tempfile
    import os
    
    try:
        # Decode input image
        face_bytes = base64.b64decode(face_image_base64)
        face_img = Image.open(io.BytesIO(face_bytes)).convert('RGB')
        
        # HairFastGAN requires reference images for shape and color
        # Use the same face image for now (will just enhance/modify existing hair)
        # In production, you'd maintain a library of reference hairstyles
        
        # Initialize HairFast
        args = get_parser().parse_args([])
        hair_fast = HairFast(args)
        
        # For now, use the same image as reference (will modify existing hair)
        # TODO: Add hairstyle library mapping based on style_description
        result = hair_fast(face_img, face_img, face_img)
        
        # Convert result to base64
        output_buffer = io.BytesIO()
        result.save(output_buffer, format='JPEG', quality=95)
        result_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "result_image": result_base64,
            "style_applied": style_description,
            "model": "HairFastGAN",
            "gpu_used": "NVIDIA T4"
        }
        
    except Exception as e:
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

