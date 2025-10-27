#!/bin/bash
# run.sh - Quick start script for LineUp AI

echo "🚀 LineUp AI - Quick Start"
echo "=========================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found"
    echo "Creating from template..."
    if [ -f env.example.txt ]; then
        cp env.example.txt .env
        echo "✅ Created .env file"
        echo "❗ Please edit .env and add your API keys before continuing"
        echo ""
        read -p "Press Enter after adding your API keys, or Ctrl+C to exit..."
    else
        echo "❌ env.example.txt not found"
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if database exists
if [ ! -f lineup.db ]; then
    echo "🗄️  Database will be created on first run"
fi

# Start the server
echo ""
echo "✨ Starting LineUp AI server..."
echo "📍 Visit: http://localhost:5000"
echo "🛑 Press Ctrl+C to stop"
echo ""

python app_refactored.py

