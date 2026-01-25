#!/bin/bash
# Helper script to set Firebase credentials from JSON file

if [ -z "$1" ]; then
    echo "Usage: ./setup_firebase.sh <path-to-firebase-credentials.json>"
    echo ""
    echo "Example:"
    echo "  ./setup_firebase.sh ~/Downloads/lineup-firebase-adminsdk.json"
    exit 1
fi

JSON_FILE="$1"

if [ ! -f "$JSON_FILE" ]; then
    echo "❌ File not found: $JSON_FILE"
    exit 1
fi

# Read JSON and export as environment variable
export FIREBASE_CREDENTIALS=$(cat "$JSON_FILE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))")

echo "✅ FIREBASE_CREDENTIALS set!"
echo ""
echo "Project ID: $(cat "$JSON_FILE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('project_id', 'N/A'))")"
echo ""
echo "🚀 Now you can run: python3 app.py"
echo ""
echo "💡 To make this permanent, add to your shell profile:"
echo "   export FIREBASE_CREDENTIALS='$(cat "$JSON_FILE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))")'"
