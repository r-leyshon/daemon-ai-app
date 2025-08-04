import os

def get_cors_origins():
    """Get CORS origins - hardcoded for simplicity"""
    # Always include localhost for development
    origins = ["http://localhost:3000"]
    
    # In production, allow all Vercel domains for this project
    if os.getenv("VERCEL"):
        origins.extend([
            "https://daemon-ai-app-r-leyshons-projects.vercel.app",
            "https://daemon-ai-app-r-leyshon-r-leyshons-projects.vercel.app",
            # Allow any subdomain of your Vercel project
            "https://daemon-ai-r-leyshon*.vercel.app",
            "https://daemon-ai-app.vercel.app"
        ])
    
    return origins 