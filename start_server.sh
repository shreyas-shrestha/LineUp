#!/bin/bash
# Start LineUp server with Firebase credentials

# Load Firebase credentials from JSON file
export FIREBASE_CREDENTIALS=$(cat finallineup-117a0-firebase-adminsdk-fbsvc-90cc6af3d4.json | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))")

echo "✅ Firebase credentials loaded"
echo "🚀 Starting LineUp server..."
echo ""

python3 app.py
