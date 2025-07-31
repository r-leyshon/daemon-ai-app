#!/bin/bash

echo "🎨 Starting Daemon AI Frontend"
echo "=============================="

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🌟 Starting Next.js development server..."
echo "📍 Frontend: http://localhost:3000"
echo "🔄 Auto-reload enabled"
echo ""

npm run dev
