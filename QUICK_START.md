# Quick Start Guide

## 🚀 Get the Daemon AI App Running in 3 Steps

### Step 1: Setup (One-time only)
\`\`\`bash
# Make scripts executable
chmod +x setup.sh start-backend.sh start-frontend.sh

# Run setup
./setup.sh
\`\`\`

### Step 2: Get Your OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new API key
3. Copy it for the next step

### Step 3: Start the Application

**Option A: Manual (Recommended for first time)**

Terminal 1 (Backend):
\`\`\`bash
export OPENAI_API_KEY='your-api-key-here'
./start-backend.sh
\`\`\`

Terminal 2 (Frontend):
\`\`\`bash
./start-frontend.sh
\`\`\`

**Option B: Automatic**
\`\`\`bash
export OPENAI_API_KEY='your-api-key-here'
npm run dev:full
\`\`\`

### Step 4: Open the App
Visit [http://localhost:3000](http://localhost:3000)

---

## 🔧 Troubleshooting

### "Cannot connect to backend" error
- Make sure the backend is running on port 8000
- Check that your OpenAI API key is set
- Visit http://localhost:8000/health to test the backend

### "Module not found" errors
- Run `./setup.sh` again
- Make sure you're using Python 3.7+

### OpenAI API errors
- Verify your API key is correct
- Check you have credits in your OpenAI account
- Make sure the key has the right permissions

---

## 📁 Project Structure
\`\`\`
daemon-ai-app/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── requirements.txt # Python dependencies
│   └── venv/           # Virtual environment
├── app/
│   └── page.tsx        # Next.js frontend
├── setup.sh            # One-time setup
├── start-backend.sh    # Start backend server
└── start-frontend.sh   # Start frontend server
