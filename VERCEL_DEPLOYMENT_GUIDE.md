# Vercel Deployment Guide

This guide covers deploying both the frontend and backend of the Daemon AI app to Vercel.

## Project Structure

```
daemon-ai-app/
├── app/                    # Next.js frontend (App Router)
├── backend/               # Python FastAPI backend
├── config/                # Configuration files
│   └── backend-urls.json  # Backend URLs for different environments
├── lib/                   # Utility functions
│   └── config.ts          # Configuration loader
└── components/            # React components
```

## Automatic URL Management

### Overview

This project uses Vercel's built-in environment variables for automatic URL management:

- **Frontend**: Automatically constructs backend URL from its own URL
- **Backend**: Automatically constructs frontend URL from its own URL
- **Development**: Uses localhost URLs
- **Production**: Uses Vercel's `VERCEL_URL` environment variable

### How It Works

The app automatically constructs URLs based on Vercel's naming convention:
- Frontend: `daemon-ai-xxx.vercel.app`
- Backend: `daemon-ai-backend-xxx.vercel.app`

### Environment Variables

#### Automatic (No Setup Required)
- `VERCEL_URL`: Set automatically by Vercel for each deployment
- `NODE_ENV`: Set automatically by Vercel

#### Manual Setup Required
- `OPENAI_API_KEY`: Your OpenAI API key (set manually in Vercel dashboard)

### Simple Deployment

No setup required - just deploy both services:

```bash
./deploy-simple.sh
```

Or deploy manually:

```bash
# Deploy backend
cd backend && vercel --prod

# Deploy frontend  
cd .. && vercel --prod
```

## Frontend Deployment

### Prerequisites

- Vercel CLI installed (`npm i -g vercel`)
- Node.js 18+ installed

### Deployment Steps

1. **Navigate to project root:**
   ```bash
   cd /path/to/daemon-ai-app
   ```

2. **Deploy to Vercel:**
   ```bash
   vercel --prod
   ```

3. **Verify deployment:**
   - Visit the provided URL
   - Check that the app loads correctly
   - Test backend connectivity

### Configuration

The frontend automatically uses the correct backend URL based on the environment:
- **Development**: Uses `http://localhost:8000`
- **Production**: Uses the URL from `config/backend-urls.json`

## Backend Deployment

### Prerequisites

- Vercel CLI installed
- Python 3.9+ (for local testing)
- OpenAI API key configured in Vercel environment variables

### Deployment Steps

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Deploy to Vercel:**
   ```bash
   vercel --prod
   ```

3. **Configure environment variables:**
   - Go to Vercel dashboard
   - Navigate to your backend project
   - Add `OPENAI_API_KEY` environment variable

### File Structure

```
backend/
├── main.py              # FastAPI application
├── api/
│   └── index.py         # Vercel entry point
├── requirements.txt     # Python dependencies
└── vercel.json         # Vercel configuration
```

### Configuration Files

#### `backend/vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

#### `backend/api/index.py`
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export the FastAPI app as 'app' for Vercel's ASGI support
```

#### `backend/requirements.txt`
```
fastapi==0.104.1
uvicorn==0.24.0
openai==1.98.0
pydantic==2.5.0
httpx==0.24.1
python-dotenv==1.0.0
```

## Environment Variables

### Frontend
- `NODE_ENV`: Automatically set by Vercel

### Backend
- `OPENAI_API_KEY`: Your OpenAI API key
- `VERCEL`: Automatically set by Vercel (indicates production environment)

## Troubleshooting

### Common Issues

1. **Backend Function Invocation Failed**
   - Check Vercel logs for specific errors
   - Verify all dependencies are in `requirements.txt`
   - Ensure environment variables are set

2. **Frontend Can't Connect to Backend**
   - Verify the backend URL in `config/backend-urls.json`
   - Check that the backend is deployed and healthy
   - Test the backend URL directly with curl

3. **Import Errors**
   - Ensure all required packages are in `requirements.txt`
   - Check that the Python version is compatible

### Debugging Commands

```bash
# Test backend health
curl https://your-backend-url.vercel.app/health

# Check backend logs
vercel logs https://your-backend-url.vercel.app

# Test frontend deployment
curl https://your-frontend-url.vercel.app
```

## Maintenance

### Regular Tasks

1. **Update backend URLs** when redeploying
2. **Monitor Vercel usage** to stay within limits
3. **Keep dependencies updated** in both frontend and backend
4. **Test deployments** before updating production URLs

### Backup Strategy

- Keep local copies of configuration files
- Document any manual configuration steps
- Use version control for all configuration changes 