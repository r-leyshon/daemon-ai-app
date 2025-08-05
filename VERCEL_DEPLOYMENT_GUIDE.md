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
- `OPENAI_API_KEY`: Your OpenAI API key (set via Vercel CLI or dashboard)

## Vercel Deployment Quickstart

### Prerequisites

Before deploying, ensure you have:

1. **OpenAI API Key**: Get yours from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. **Local environment setup**: Copy `.env.example` to `.env` and add your API key
3. **Vercel CLI**: Install with `npm install -g vercel`

### Quick Deploy

1. **Set up backend environment variable:**
   ```bash
   cd backend
   vercel env add OPENAI_API_KEY
   # Enter your OpenAI API key when prompted
   ```

2. **Deploy backend:**
   ```bash
   vercel --prod
   ```

3. **Deploy frontend:**
   ```bash
   cd .. && vercel --prod
   ```

That's it! No URL updates needed.

### How It Works

We use Vercel's stable project URLs that automatically point to the latest deployment:

- **Backend**: `https://daemon-ai-backend-r-leyshons-projects.vercel.app`
- **Frontend**: `https://daemon-ai-app-r-leyshons-projects.vercel.app`

These URLs never change, so you never need to update configuration files.

### Key Benefits

- **No URL updates required** - Project URLs are stable
- **Simple deployment** - Just deploy both services
- **Works every time** - No configuration changes needed
- **Automatic** - Vercel handles pointing to latest deployments
- **CORS works out of the box** - Stable URLs prevent cross-origin issues
- **No deployment loops** - No need to update URLs after deployment

### Cross-Origin (CORS) Configuration

The backend is configured to allow requests from the frontend using stable URLs:

#### Backend CORS Setup: `backend/config.py`
```python
def get_cors_origins():
    """Get CORS origins - uses stable project URLs"""
    # Always include localhost for development
    origins = ["http://localhost:3000"]

    # In production, add the stable frontend project URL
    if os.getenv("VERCEL"):
        origins.append("https://daemon-ai-app-r-leyshons-projects.vercel.app")

    return origins
```

This ensures the backend accepts requests from:
- ✅ Local development: `http://localhost:3000`
- ✅ Production frontend: `https://daemon-ai-app-r-leyshons-projects.vercel.app`

### Frontend Configuration

#### API Base URL: `lib/config.ts`
```typescript
export const getApiBaseUrl = (): string => {
  // In development, use localhost
  if (process.env.NODE_ENV !== 'production') {
    return "http://localhost:8000"
  }
  // In production, use the stable backend project URL
  return "https://daemon-ai-backend-r-leyshons-projects.vercel.app"
}
```

This ensures the frontend connects to:
- ✅ Local development: `http://localhost:8000`
- ✅ Production backend: `https://daemon-ai-backend-r-leyshons-projects.vercel.app`

### Quickstart Troubleshooting

If you see CORS errors, ensure:
1. Backend is deployed and healthy
2. Frontend is using the correct stable backend URL
3. Backend CORS includes the correct stable frontend URL
4. Both services are using project URLs (not deployment-specific URLs)

## Frontend Deployment (Detailed)

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

### Configuration Details

The frontend automatically uses the correct backend URL based on the environment:
- **Development**: Uses `http://localhost:8000`
- **Production**: Uses the stable backend project URL

## Backend Deployment (Detailed)

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

### Environment Variable Configuration

**Option A: Using Vercel CLI (Recommended)**
```bash
vercel env add OPENAI_API_KEY
```
- Enter your OpenAI API key when prompted
- Select "Production" environment

**Option B: Using Vercel Dashboard**
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

## Updating Environment Variables

### Updating OpenAI API Key

If you need to update your OpenAI API key:

1. **Update local development:**
   - Edit your `.env` file in the project root
   - Replace the existing `OPENAI_API_KEY` value

2. **Update Vercel deployment:**
   ```bash
   cd backend
   vercel env rm OPENAI_API_KEY
   vercel env add OPENAI_API_KEY
   ```
   - Enter your new API key when prompted
   - Select "Production" environment

3. **Redeploy to apply changes:**
   ```bash
   vercel --prod
   ```

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