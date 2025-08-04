# Daemon AI Assistant

AI assistants that live alongside your text, offering contextual suggestions.

## Inspiration

This project is inspired by [Maggie Appleton's "Daemons" concept](https://maggieappleton.com/lm-sketchbook) from her Language Model Sketchbook. The idea of having AI assistants with specific personalities that live alongside your text and offer contextual suggestions comes directly from her brilliant exploration of non-chatbot interfaces for language models.

## Overview

Daemon AI Assistant is a Next.js application that provides AI-powered writing assistance through specialized "daemons" - each with their own personality and expertise. The daemons analyze your text and provide contextual suggestions for improvement.

## Features

- **Multiple AI Daemons**: Devil's Advocate, Grammar Enthusiast, Clarity Coach
- **Contextual Highlighting**: Daemons highlight relevant text sections
- **Interactive Suggestions**: Click on daemons to get specific feedback
- **Real-time Analysis**: Get suggestions as you write

## Tech Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: Python FastAPI with OpenAI integration
- **Deployment**: Vercel (both frontend and backend)

## Quick Start

### Prerequisites

- Node.js 18+ and npm/pnpm
- Python 3.9+
- OpenAI API key
- Vercel CLI: `npm install -g vercel`

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd daemon-ai-app
   ```

2. **Install frontend dependencies**
   ```bash
   npm install
   # or
   pnpm install
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file in project root
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

4. **Start the backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

5. **Start the frontend**
   ```bash
   # In a new terminal, from project root
   npm run dev
   # or
   pnpm dev
   ```

6. **Open your browser**
   Navigate to `http://localhost:3000`

## Deployment

This project is configured for deployment on Vercel. See [VERCEL_DEPLOYMENT_GUIDE.md](./VERCEL_DEPLOYMENT_GUIDE.md) for detailed deployment instructions.

### Quick Deploy

1. **Deploy Backend**
   ```bash
   cd backend
   vercel --prod
   ```

2. **Deploy Frontend**
   ```bash
   # From project root
   vercel --prod
   ```

3. **Set Environment Variables**
   ```bash
   # In backend directory
   vercel env add OPENAI_API_KEY production
   ```

## Project Structure

```
daemon-ai-app/
├── app/                    # Next.js frontend (App Router)
├── components/             # React components
├── lib/                    # Utilities
├── public/                 # Static assets
├── backend/                # Python FastAPI backend
│   ├── api/
│   │   └── index.py        # Main API handler
│   ├── requirements.txt    # Python dependencies
│   └── vercel.json         # Backend Vercel config
├── .vercelignore           # Files to exclude from frontend deployment
├── package.json            # Frontend dependencies
├── next.config.mjs         # Next.js config
└── README.md
```

## Available Daemons

### Devil's Advocate
- **Color**: Red (#e74c3c)
- **Purpose**: Questions assertions and asks for evidence
- **Example**: "What evidence supports this claim?"

### Grammar Enthusiast
- **Color**: Purple (#9b59b6)
- **Purpose**: Identifies grammatical and style issues
- **Example**: "Are there any grammatical issues in this text?"

### Clarity Coach
- **Color**: Blue (#3498db)
- **Purpose**: Suggests ways to improve clarity
- **Example**: "Could this be expressed more clearly?"

For deployment issues, see the [Vercel Deployment Guide](./VERCEL_DEPLOYMENT_GUIDE.md).
