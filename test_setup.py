#!/usr/bin/env python3
"""Quick test to verify v2 setup."""

import os
import sys

print("🔍 Testing LineUp v2 Setup...\n")

# Test imports
print("1. Testing imports...")
try:
    from lineup_backend.db.firestore_client import get_firestore_client
    print("   ✅ Database imports successful")
except Exception as e:
    print(f"   ❌ Database import failed: {e}")
    sys.exit(1)

try:
    from lineup_backend.middleware.auth import require_auth, require_barber_auth
    print("   ✅ Auth middleware imports successful")
except Exception as e:
    print(f"   ❌ Auth middleware import failed: {e}")
    sys.exit(1)

try:
    from lineup_backend.db.repositories import (
        UserRepository, SocialRepository, AppointmentRepository
    )
    print("   ✅ Repository imports successful")
except Exception as e:
    print(f"   ❌ Repository import failed: {e}")
    sys.exit(1)

# Test Firestore connection
print("\n2. Testing Firestore connection...")
firestore = get_firestore_client()
if firestore.is_available:
    print("   ✅ Firestore is available and connected")
    
    # Test a simple operation
    try:
        test_collection = firestore.get_collection("_test_connection")
        if test_collection:
            print("   ✅ Can access Firestore collections")
        else:
            print("   ⚠️  Firestore client exists but collections not accessible")
    except Exception as e:
        print(f"   ⚠️  Firestore connection test failed: {e}")
else:
    print("   ⚠️  Firestore not available")
    print("   💡 Set FIREBASE_CREDENTIALS environment variable to enable")
    print("   💡 Or set LINEUP_DISABLE_AUTH=true for development mode")

# Test environment variables
print("\n3. Checking environment variables...")
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")
if firebase_creds:
    print("   ✅ FIREBASE_CREDENTIALS is set")
    try:
        import json
        creds_dict = json.loads(firebase_creds)
        if "project_id" in creds_dict:
            print(f"   ✅ Project ID: {creds_dict['project_id']}")
        else:
            print("   ⚠️  FIREBASE_CREDENTIALS missing project_id")
    except Exception as e:
        print(f"   ⚠️  FIREBASE_CREDENTIALS is invalid JSON: {e}")
else:
    print("   ⚠️  FIREBASE_CREDENTIALS not set")

disable_auth = os.environ.get("LINEUP_DISABLE_AUTH")
if disable_auth == "true":
    print("   ✅ LINEUP_DISABLE_AUTH=true (development mode)")
else:
    print("   ℹ️  LINEUP_DISABLE_AUTH not set (production mode)")

# Test repository instantiation
print("\n4. Testing repository instantiation...")
try:
    user_repo = UserRepository()
    social_repo = SocialRepository()
    appt_repo = AppointmentRepository()
    print("   ✅ All repositories can be instantiated")
except Exception as e:
    print(f"   ❌ Repository instantiation failed: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("🎉 Setup check complete!")
print("="*50)
print("\nNext steps:")
print("1. If Firestore is not available, set FIREBASE_CREDENTIALS")
print("2. Start the Flask app: python app.py")
print("3. Test endpoints: curl http://localhost:5000/health")
print("4. Test auth: curl http://localhost:5000/auth/me")
