import os

def get_cors_origins():
    """Get CORS origins - hardcoded for simplicity"""
    # Always include localhost for development
    origins = ["http://localhost:3000"]
    
    # In production, add the stable frontend project URL (doesn't change with deployments)
    if os.getenv("VERCEL"):
        origins.append("https://daemon-ai-app-r-leyshons-projects.vercel.app")
    
    return origins 