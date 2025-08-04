#!/bin/bash

# Simple Daemon AI App Deployment
# No setup required - just deploy both services

echo "🚀 Deploying Daemon AI App..."

# Deploy backend
echo "📦 Deploying backend..."
cd backend
vercel --prod
cd ..

# Deploy frontend
echo "📦 Deploying frontend..."
vercel --prod

echo "🎉 Deployment complete!"
echo ""
echo "The app will automatically connect frontend to backend using Vercel's built-in environment variables."
echo ""
echo "Note: You may need to disable Vercel authentication in the dashboard"
echo "if you want public access to the frontend." 