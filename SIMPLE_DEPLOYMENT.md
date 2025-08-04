# Simple Deployment Guide

This is the simplest possible deployment approach - using stable project URLs that don't change.

## Quick Deploy

1. **Deploy backend:**
   ```bash
   cd backend && vercel --prod
   ```

2. **Deploy frontend:**
   ```bash
   cd .. && vercel --prod
   ```

That's it! No URL updates needed.

## How It Works

We use Vercel's stable project URLs that automatically point to the latest deployment:

- **Backend**: `https://daemon-ai-backend-r-leyshons-projects.vercel.app`
- **Frontend**: `https://daemon-ai-app-r-leyshons-projects.vercel.app`

These URLs never change, so you never need to update configuration files.

## Cross-Origin (CORS) Configuration

The backend is configured to allow requests from the frontend using stable URLs:

### Backend CORS Setup: `backend/config.py`
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

## Frontend Configuration

### API Base URL: `lib/config.ts`
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

## Key Benefits

- **No URL updates required** - Project URLs are stable
- **Simple deployment** - Just deploy both services
- **Works every time** - No configuration changes needed
- **Automatic** - Vercel handles pointing to latest deployments
- **CORS works out of the box** - Stable URLs prevent cross-origin issues
- **No deployment loops** - No need to update URLs after deployment

## Troubleshooting

If you see CORS errors, ensure:
1. Backend is deployed and healthy
2. Frontend is using the correct stable backend URL
3. Backend CORS includes the correct stable frontend URL
4. Both services are using project URLs (not deployment-specific URLs) 