#!/bin/bash

echo "🚀 Starting Daemon AI Backend Server"
echo "===================================="

# Check if we're in the backend directory
if [ ! -f "main.py" ]; then
    echo "📁 Navigating to backend directory..."
    cd backend
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run the setup script first: ./setup.sh"
    exit 1
fi

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OpenAI API key not found!"
    echo "Please set your API key:"
    echo "export OPENAI_API_KEY='your-api-key-here'"
    echo ""
    read -p "Enter your OpenAI API key: " api_key
    export OPENAI_API_KEY="$api_key"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Start the server
echo "🌟 Starting FastAPI server..."
echo "📍 Backend: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🔄 Auto-reload enabled"
echo ""

python main.py
