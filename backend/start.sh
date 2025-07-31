#!/bin/bash
echo "Starting Daemon AI Backend..."
echo "Make sure you have set your OPENAI_API_KEY environment variable"
echo ""

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  WARNING: OPENAI_API_KEY environment variable is not set!"
    echo "Please set it with: export OPENAI_API_KEY='your-api-key-here'"
    echo ""
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting FastAPI server on http://localhost:8000"
echo "API docs will be available at http://localhost:8000/docs"
echo ""

python main.py
