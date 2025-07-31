# Daemon AI Assistant

A proof-of-concept implementation of Maggie Appleton's "daemon" AI concept - AI assistants that live alongside your text as contextual margin markers, offering suggestions and critiques.

## Features

- **Inline Daemon Markers**: Colored dots in the margin that correspond to different AI personas
- **Contextual Suggestions**: Each daemon analyzes your text and offers relevant questions/suggestions
- **Interactive Tooltips**: Hover or click markers to see suggestions and get detailed answers
- **Custom Daemons**: Create your own AI assistants with custom prompts and personalities
- **Real-time Analysis**: Text is analyzed as you type or edit

## Architecture

- **Frontend**: Next.js with React components for interactive UI
- **Backend**: FastAPI with OpenAI integration for AI-powered suggestions
- **Communication**: REST API with CORS enabled for local development

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   \`\`\`bash
   cd backend
   \`\`\`

2. Install Python dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

3. Set up your OpenAI API key:
   \`\`\`bash
   export OPENAI_API_KEY="your-api-key-here"
   \`\`\`
   Or create a `.env` file with your API key.

4. Run the FastAPI server:
   \`\`\`bash
   python main.py
   \`\`\`
   The API will be available at `http://localhost:8000`

### Frontend Setup

1. Install dependencies:
   \`\`\`bash
   npm install
   \`\`\`

2. Run the development server:
   \`\`\`bash
   npm run dev
   \`\`\`
   The app will be available at `http://localhost:3000`

## Usage

1. **View Sample Text**: The app loads with sample text about language models
2. **See Daemon Suggestions**: Colored markers appear in the right margin
3. **Interact with Daemons**: 
   - Hover over markers to see daemon names
   - Click markers to see their questions/suggestions
   - Click "Show Answer" to get detailed AI responses
4. **Add Custom Daemons**: Click the "Add Daemon" button to create your own AI assistants
5. **Edit Text**: Modify the text in the textarea to see new suggestions

## Default Daemons

- **Devil's Advocate** (Red): Questions assertions and asks for evidence
- **Summarizer** (Green): Suggests ways to make text more concise
- **Evidence Finder** (Blue): Identifies claims needing citations
- **Clarity Coach** (Purple): Points out unclear or confusing passages

## Technical Details

- Uses OpenAI's GPT-3.5-turbo for generating suggestions and answers
- In-memory storage for daemon definitions (resets on server restart)
- CORS enabled for local development
- Responsive design with Tailwind CSS
- TypeScript for type safety

## Future Enhancements

- Persistent storage for custom daemons
- Real-time suggestions as you type
- Multi-user support with authentication
- More sophisticated text parsing and span detection
- Integration with external knowledge bases
- Export/import daemon configurations

## Inspiration

Based on Maggie Appleton's "Language Model Sketchbook" concept of daemon-like AI assistants that provide contextual help during writing.
