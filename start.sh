#!/bin/bash

echo "🚀 Starting SqueezeSeeker Trading Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check for Alpaca credentials
if [ ! -f "$HOME/.openclaw/secrets/alpaca.json" ]; then
    echo "⚠️  WARNING: Alpaca credentials not found at ~/.openclaw/secrets/alpaca.json"
    echo "Please create the file with your API credentials before proceeding."
    exit 1
fi

echo ""
echo "✅ All set! Starting dashboard..."
echo ""
echo "📊 Dashboard will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Flask app
python app.py
