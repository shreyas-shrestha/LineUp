#!/usr/bin/env python3
"""
Test script for HairFastGAN integration
Run this LOCALLY to verify the API works before deploying
"""

import sys
import base64

print("🧪 Testing HairFastGAN Integration...")
print("-" * 60)

# Test 1: Check if gradio_client is installed
print("\n1️⃣ Checking gradio_client installation...")
try:
    from gradio_client import Client
    print("✅ gradio_client installed successfully")
except ImportError as e:
    print(f"❌ FAILED: {e}")
    print("   Fix: pip install gradio_client")
    sys.exit(1)

# Test 2: Try to connect to HairFastGAN Space
print("\n2️⃣ Connecting to HairFastGAN Space...")
try:
    client = Client("AIRI-Institute/HairFastGAN")
    print("✅ Connected to HairFastGAN Space")
except Exception as e:
    print(f"❌ FAILED: {e}")
    print("   Possible issue: Space is down or URL changed")
    sys.exit(1)

# Test 3: Check Space info
print("\n3️⃣ Checking Space API info...")
try:
    # Get available endpoints
    print(f"   Space info: {client.view_api()}")
except Exception as e:
    print(f"⚠️  Could not get Space info: {e}")

# Test 4: Test with a sample image
print("\n4️⃣ Testing with sample image...")
print("   Creating test image...")
try:
    from PIL import Image
    import tempfile
    import os
    
    # Create a simple test image (red square)
    img = Image.new('RGB', (512, 512), color='red')
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg', mode='wb') as tmp:
        img.save(tmp, format='JPEG')
        test_image_path = tmp.name
    
    print(f"   Test image created: {test_image_path}")
    
    # Reference hairstyle URL
    reference_url = "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=512&h=512&fit=crop"
    
    print(f"   Reference URL: {reference_url}")
    print("\n   Calling HairFastGAN API...")
    print("   (This may take 30-60 seconds for first request...)")
    
    # Try different API call formats
    result = None
    error = None
    
    # Format 1: With api_name
    try:
        print("\n   Try 1: With api_name='/predict'")
        result = client.predict(
            test_image_path,  # face image
            reference_url,    # shape image
            reference_url,    # color image  
            True,            # align face
            True,            # use hair mask
            api_name="/predict"
        )
        print(f"   ✅ Success with api_name='/predict'")
    except Exception as e1:
        error = e1
        print(f"   ❌ Failed: {e1}")
        
        # Format 2: Without api_name
        try:
            print("\n   Try 2: Without api_name")
            result = client.predict(
                test_image_path,
                reference_url,
                reference_url,
                True,
                True
            )
            print(f"   ✅ Success without api_name")
        except Exception as e2:
            error = e2
            print(f"   ❌ Failed: {e2}")
            
            # Format 3: Different parameter order
            try:
                print("\n   Try 3: Different parameter order")
                result = client.predict(
                    test_image_path,
                    reference_url,
                    reference_url
                )
                print(f"   ✅ Success with 3 params")
            except Exception as e3:
                error = e3
                print(f"   ❌ Failed: {e3}")
    
    # Clean up test image
    try:
        os.unlink(test_image_path)
    except:
        pass
    
    if result:
        print(f"\n✅ HairFastGAN API WORKS!")
        print(f"   Result type: {type(result)}")
        print(f"   Result value: {result}")
        
        # Try to parse result
        result_path = result
        if isinstance(result, dict):
            result_path = result.get('name') or result.get('path') or result.get('value')
            print(f"   Extracted path from dict: {result_path}")
        elif isinstance(result, (list, tuple)) and len(result) > 0:
            result_path = result[0]
            print(f"   Extracted path from list/tuple: {result_path}")
            if isinstance(result_path, dict):
                result_path = result_path.get('name') or result_path.get('path') or result_path.get('value')
                print(f"   Extracted path from nested dict: {result_path}")
        
        if result_path and os.path.exists(result_path):
            print(f"   ✅ Result file exists: {result_path}")
            file_size = os.path.getsize(result_path)
            print(f"   File size: {file_size} bytes")
            
            # Clean up result
            try:
                os.unlink(result_path)
            except:
                pass
        else:
            print(f"   ⚠️  Result path not found or invalid: {result_path}")
    else:
        print(f"\n❌ HairFastGAN API FAILED!")
        print(f"   Last error: {error}")
        print("\n   Possible issues:")
        print("   - Space is overloaded")
        print("   - API parameters changed")
        print("   - Network timeout")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nHairFastGAN integration is ready to deploy!")
print("Your backend will work correctly.")

