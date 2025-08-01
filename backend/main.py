from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
from openai import OpenAI
import re
import uuid
from dotenv import load_dotenv
import pathlib

# Load environment variables from .env file in project root
# Go up from backend/main.py to project root
project_root = pathlib.Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# Debug: Check if API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in environment variables")
    print(f"Project root: {project_root}")
    print(f"Looking for .env file at: {env_path}")
    print(f"File exists: {env_path.exists()}")
    exit(1)
else:
    print(f"✅ OpenAI API key loaded successfully (ending: ...{api_key[-4:]})")

# Initialize OpenAI client with the validated API key
client = OpenAI(api_key=api_key)
print("✅ OpenAI client initialized successfully")

app = FastAPI(title="Daemon AI API", description="Backend for daemon-like AI assistants")

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class Daemon(BaseModel):
    id: Optional[str] = None
    name: str
    prompt: str
    examples: List[Dict[str, str]] = []
    guardrails: Optional[str] = None
    color: str

class TextInput(BaseModel):
    text: str

class Suggestion(BaseModel):
    daemon_id: str
    daemon_name: str
    question: str
    span_text: Optional[str] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    color: str

class AnswerRequest(BaseModel):
    daemon_id: str
    question: str
    span_text: str

class AnswerResponse(BaseModel):
    daemon_id: str
    question: str
    answer: str

# In-memory daemon storage
daemons: Dict[str, Daemon] = {}

# Initialize with default daemons
def initialize_default_daemons():
    default_daemons = [
        Daemon(
            id="devil_advocate",
            name="Devil's Advocate",
            prompt="You are a devil's advocate AI that questions assertions and asks for evidence. Challenge claims constructively and point out potential counterarguments.",
            examples=[
                {"user": "LLMs are always unreliable.", "assistant": "Is this claim too absolute? Are there specific contexts where LLMs might be more reliable?"}
            ],
            guardrails="Stay polite and constructive. Ask only one pointed question. Focus on evidence and logical reasoning.",
            color="#e74c3c"
        ),
        Daemon(
            id="grammar_enthusiast",
            name="Grammar Enthusiast",
            prompt="You are a grammar and style enthusiast who helps improve writing mechanics, sentence structure, and clarity. Focus on specific grammatical issues and style improvements.",
            examples=[
                {"user": "The data shows that it's results are promising.", "assistant": "Should 'it's' be 'its' here? Also, consider if 'the results' would be clearer than 'it's results'."}
            ],
            guardrails="Focus on specific grammar, punctuation, or style issues. Be helpful and educational, not pedantic.",
            color="#9b59b6"
        ),
        Daemon(
            id="clarity_coach",
            name="Clarity Coach",
            prompt="You help improve writing clarity by identifying confusing, vague, or unnecessarily complex passages. Suggest specific ways to make ideas clearer.",
            examples=[
                {"user": "The implementation of the solution was done in a way that was effective.", "assistant": "Could you be more specific about what was implemented and how it was effective?"}
            ],
            guardrails="Focus on specific clarity issues. Suggest concrete improvements rather than general advice.",
            color="#3498db"
        )
    ]
    
    for daemon in default_daemons:
        daemons[daemon.id] = daemon

# Initialize on startup
initialize_default_daemons()

def find_text_span(text: str, question: str) -> tuple[str, int, int]:
    """Find the most relevant text span for a question using AI."""
    try:
        # Use AI to identify the specific text span that should be highlighted
        messages = [
            {
                "role": "system",
                "content": """You are a text analysis assistant. Given a question about a text, identify the specific text span (exact words/phrases) that should be highlighted to show the issue being discussed.

IMPORTANT: 
- Return ONLY the exact text span that should be highlighted, nothing else. Do not include quotes or explanations.
- Only highlight text that ACTUALLY EXISTS in the original text.
- If the issue mentioned in the question does not exist in the text, return "NO_HIGHLIGHT"."""
            },
            {
                "role": "user",
                "content": f"""TEXT:
"{text}"

QUESTION: {question}

What specific text span should be highlighted to show the issue being discussed? Return only the exact words/phrases."""
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=messages,
        )
        
        span_text = response.choices[0].message.content.strip().strip('"').strip("'")
        
        # Check if AI found no issues or no highlight needed
        if "no specific issues found" in span_text.lower() or "no_highlight" in span_text.lower():
            # Return empty span to indicate no highlighting needed
            return "", 0, 0
        
        # Find the span in the original text
        span_lower = span_text.lower()
        text_lower = text.lower()
        
        # Try to find exact match first
        start_pos = text_lower.find(span_lower)
        
        if start_pos != -1:
            # Found exact match
            end_pos = start_pos + len(span_text)
            return span_text, start_pos, end_pos
        
        # If no exact match, try to find the closest match
        # Split into words and find the best partial match
        span_words = span_text.split()
        if len(span_words) > 0:
            # Find the first word of the span
            first_word = span_words[0]
            start_pos = text_lower.find(first_word)
            
            if start_pos != -1:
                # Find a reasonable end point (try to include more words from the span)
                end_pos = start_pos + len(first_word)
                
                # Try to extend to include more words from the span
                for word in span_words[1:]:
                    next_pos = text_lower.find(word, end_pos)
                    if next_pos != -1 and next_pos - end_pos < 50:  # Within reasonable distance
                        end_pos = next_pos + len(word)
                    else:
                        break
                
                return text[start_pos:end_pos], start_pos, end_pos
        
        # Fallback: return the first sentence if no match found
        end = text.find('.')
        end = end + 1 if end != -1 else min(100, len(text))
        fallback_text = text[:end].strip()
        return fallback_text, 0, end
        
    except Exception as e:
        print(f"Error in AI-based text span finding: {e}")
        # Fallback to original logic
        words = re.findall(r'\b\w{4,}\b', question.lower())
        
        best_match = ""
        best_start = 0
        best_end = 0
        
        for word in words:
            if word in text.lower():
                word_pos = text.lower().find(word)
                start = text.rfind('.', 0, word_pos)
                start = start + 1 if start != -1 else 0
                end = text.find('.', word_pos)
                end = end + 1 if end != -1 else len(text)
                sentence = text[start:end].strip()
                
                if len(sentence) > len(best_match):
                    best_match = sentence
                    best_start = start
                    best_end = end
        
        if not best_match:
            end = text.find('.')
            end = end + 1 if end != -1 else min(100, len(text))
            best_match = text[:end].strip()
            best_start = 0
            best_end = end
        
        return best_match, best_start, best_end

def generate_suggestion_for_daemon(text: str, daemon: Daemon) -> str:
    """Generate a suggestion/question for the given text and daemon."""
    try:
        # Build messages for OpenAI
        messages = [
            {
                "role": "system", 
                "content": f"{daemon.prompt} {daemon.guardrails or ''}"
            }
        ]
        
        # Add examples if available
        for example in daemon.examples:
            messages.append({"role": "user", "content": example["user"]})
            messages.append({"role": "assistant", "content": example["assistant"]})
        
        # Add the actual task
        user_content = f"""TEXT:
"{text}"

As a {daemon.name}, identify one specific issue or opportunity for improvement that ACTUALLY EXISTS in this text. 

IMPORTANT: Only identify issues that are actually present in the text. Do not make up or hallucinate problems that don't exist. If you cannot find any relevant issues in this text, respond with "No specific issues found in this text."

Your question should be actionable and help the writer improve their work."""
        
        messages.append({"role": "user", "content": user_content})
        
        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=100,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error generating suggestion: {e}")
        return f"[{daemon.name}] What could be improved in this section?"

def generate_answer(question: str, context: str, daemon: Daemon) -> str:
    """Generate an answer for a daemon's question."""
    try:
        messages = [
            {
                "role": "system",
                "content": f"You are responding as the {daemon.name}. {daemon.guardrails or ''}"
            },
            {
                "role": "user",
                "content": f"""Context: "{context}"

Question: {question}

Provide a helpful, specific answer or suggestion that addresses this question. Be constructive and actionable."""
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error generating answer: {e}")
        return "I apologize, but I'm having trouble generating a response right now. Please try again."

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Daemon AI Backend is running"}

@app.get("/daemons")
def list_daemons():
    """Get all available daemons."""
    return {"daemons": list(daemons.values())}

@app.post("/daemons")
def add_daemon(daemon: Daemon):
    """Add a new daemon."""
    daemon_id = daemon.id or str(uuid.uuid4())
    daemon.id = daemon_id
    daemons[daemon_id] = daemon
    return {"id": daemon_id, "status": "added", "daemon": daemon}

@app.delete("/daemons/{daemon_id}")
def delete_daemon(daemon_id: str):
    """Delete a daemon by ID."""
    if daemon_id not in daemons:
        raise HTTPException(status_code=404, detail="Daemon not found")
    
    # Don't allow deletion of default daemons (optional safeguard)
    default_daemon_ids = {"devil_advocate", "grammar_enthusiast", "clarity_coach"}
    if daemon_id in default_daemon_ids:
        raise HTTPException(status_code=400, detail="Cannot delete default daemons")
    
    deleted_daemon = daemons.pop(daemon_id)
    return {"id": daemon_id, "status": "deleted", "daemon": deleted_daemon}

@app.post("/suggestions")
def get_suggestions(input_data: TextInput):
    """Generate suggestions for the given text from all daemons."""
    text = input_data.text
    suggestions = []
    
    print(f"Processing text: {text[:100]}...")  # Debug log
    
    for daemon_id, daemon in daemons.items():
        try:
            print(f"Processing daemon: {daemon.name}")  # Debug log
            question = generate_suggestion_for_daemon(text, daemon)
            span_text, start_idx, end_idx = find_text_span(text, question)
            
            suggestion = Suggestion(
                daemon_id=daemon_id,
                daemon_name=daemon.name,
                question=question,
                span_text=span_text,
                start_index=start_idx,
                end_index=end_idx,
                color=daemon.color
            )
            suggestions.append(suggestion)
            print(f"Generated suggestion for {daemon.name}: {question}")  # Debug log
        except Exception as e:
            print(f"Error processing daemon {daemon_id}: {e}")
            continue
    
    print(f"Returning {len(suggestions)} suggestions")  # Debug log
    return {"suggestions": suggestions}

@app.post("/suggestion/{daemon_id}")
def get_suggestion_from_daemon(daemon_id: str, input_data: TextInput):
    """Generate a suggestion for the given text from a specific daemon."""
    daemon = daemons.get(daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")
    
    text = input_data.text
    
    try:
        print(f"Processing text with {daemon.name}: {text[:100]}...")  # Debug log
        question = generate_suggestion_for_daemon(text, daemon)
        span_text, start_idx, end_idx = find_text_span(text, question)
        
        suggestion = Suggestion(
            daemon_id=daemon_id,
            daemon_name=daemon.name,
            question=question,
            span_text=span_text,
            start_index=start_idx,
            end_index=end_idx,
            color=daemon.color
        )
        
        print(f"Generated suggestion: {question}")  # Debug log
        print(f"Span text: '{span_text}', start: {start_idx}, end: {end_idx}")  # Debug log
        return {"suggestion": suggestion}
        
    except Exception as e:
        print(f"Error processing daemon {daemon_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestion: {str(e)}")

@app.post("/answer")
def get_answer(request: AnswerRequest):
    """Generate an answer for a specific daemon's question."""
    daemon = daemons.get(request.daemon_id)
    if not daemon:
        raise HTTPException(status_code=404, detail="Daemon not found")
    
    answer = generate_answer(request.question, request.span_text, daemon)
    
    return AnswerResponse(
        daemon_id=request.daemon_id,
        question=request.question,
        answer=answer
    )

@app.get("/health")
def health_check():
    return {"status": "healthy", "daemons_count": len(daemons)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Daemon AI Backend...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🔑 Make sure OPENAI_API_KEY is set in your environment")
    print("-" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
