export const getApiBaseUrl = (): string => {
  // In development, use localhost
  if (process.env.NODE_ENV !== 'production') {
    return "http://localhost:8000"
  }
  
  // In production, use the stable project URL (doesn't change with deployments)
  return "https://daemon-ai-backend-r-leyshons-projects.vercel.app"
}

export const getFrontendUrl = (): string => {
  // In development, use localhost
  if (process.env.NODE_ENV !== 'production') {
    return "http://localhost:3000"
  }
  
  // In production, use Vercel's URL
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`
  }
  
  // Fallback
  return "http://localhost:3000"
} 