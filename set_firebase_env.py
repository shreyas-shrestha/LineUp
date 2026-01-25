#!/usr/bin/env python3
"""Helper script to set FIREBASE_CREDENTIALS from JSON file."""

import json
import os
import sys

def set_firebase_credentials(json_file_path: str):
    """Read Firebase credentials JSON file and set as environment variable."""
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as f:
            creds = json.load(f)
        
        # Validate it has required fields
        required_fields = ['type', 'project_id', 'private_key']
        missing_fields = [field for field in required_fields if field not in creds]
        
        if missing_fields:
            print(f"❌ JSON file missing required fields: {missing_fields}")
            return False
        
        # Set as environment variable (JSON string)
        os.environ['FIREBASE_CREDENTIALS'] = json.dumps(creds)
        
        print(f"✅ FIREBASE_CREDENTIALS set from {json_file_path}")
        print(f"   Project ID: {creds['project_id']}")
        print(f"   Client Email: {creds.get('client_email', 'N/A')}")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {json_file_path}")
        print("   Make sure you've downloaded the Firebase service account JSON file")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_firebase_env.py <path-to-firebase-credentials.json>")
        print("\nExample:")
        print("  python set_firebase_env.py lineup-firebase-adminsdk.json")
        print("\nTo use it:")
        print("  python set_firebase_env.py credentials.json && python app.py")
        sys.exit(1)
    
    json_file = sys.argv[1]
    success = set_firebase_credentials(json_file)
    
    if success:
        print("\n💡 To use these credentials in this session:")
        print("   Run: python app.py")
        print("\n💡 To export for shell:")
        print(f"   export FIREBASE_CREDENTIALS='{os.environ.get('FIREBASE_CREDENTIALS')[:50]}...'")
    else:
        sys.exit(1)
