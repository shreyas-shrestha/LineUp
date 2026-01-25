#!/usr/bin/env python3
"""Prepare Firebase credentials for Render deployment."""

import json
import sys

def prepare_for_render(json_file_path: str):
    """Convert Firebase JSON to single-line string for Render."""
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as f:
            creds = json.load(f)
        
        # Convert to single-line JSON string
        creds_string = json.dumps(creds)
        
        print("="*70)
        print("FIREBASE_CREDENTIALS for Render")
        print("="*70)
        print("\nCopy this ENTIRE string and paste it as the value for")
        print("FIREBASE_CREDENTIALS in your Render dashboard:\n")
        print("-"*70)
        print(creds_string)
        print("-"*70)
        print(f"\n✅ Project ID: {creds.get('project_id', 'N/A')}")
        print(f"✅ Client Email: {creds.get('client_email', 'N/A')}")
        print("\n📋 Steps to add in Render:")
        print("1. Go to your Render dashboard")
        print("2. Select your backend service")
        print("3. Go to Environment tab")
        print("4. Add new environment variable:")
        print("   Key: FIREBASE_CREDENTIALS")
        print("   Value: (paste the string above)")
        print("5. Save and redeploy")
        print("\n" + "="*70)
        
        return creds_string
        
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        json_file = "finallineup-117a0-firebase-adminsdk-fbsvc-90cc6af3d4.json"
        print(f"No file specified, using: {json_file}\n")
    else:
        json_file = sys.argv[1]
    
    prepare_for_render(json_file)
