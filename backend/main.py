import json
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
from config import get_cors_origins

# Load environment variables from .env file in project root (for local development)
# Go up from backend/main.py to project root
project_root = pathlib.Path(__file__).parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Debug: Check if API key is loaded
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY not found in environment variables")
    print(f"Project root: {project_root}")
    print(f"Looking for .env file at: {env_path}")
    print(f"File exists: {env_path.exists()}")
    # Don't exit in production, just log the error
    if os.getenv("VERCEL") is None:
        exit(1)
else:
    print(f"✅ OpenAI API key loaded successfully (ending: ...{api_key[-4:]})")

# Initialize OpenAI client with the validated API key
client = None
try:
    if api_key:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
    else:
        print("⚠️ OpenAI API key not found, client not initialized")
except Exception as e:
    print(f"❌ Error initializing OpenAI client: {e}")
    client = None

app = FastAPI(title="Daemon AI API", description="Backend for daemon-like AI assistants")

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
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

class SuggestionResponse(BaseModel):
    """Structured response from the AI model containing both question and span information"""
    response: str
    start_index: int
    end_index: int

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

class ApplySuggestionRequest(BaseModel):
    original_text: str
    suggestion_question: str
    span_text: Optional[str] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    daemon_name: str

class ApplySuggestionResponse(BaseModel):
    improved_text: str

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



def generate_suggestion_with_span(text: str, daemon: Daemon) -> tuple[str, str, int, int]:
    """Generate a suggestion/question with text span information in a single API call."""
    try:
        if not client:
            # Fallback when OpenAI client is not available
            fallback_question = f"[{daemon.name}] OpenAI client not available. Please check API configuration."
            fallback_text = text[:100].strip()
            return fallback_question, fallback_text, 0, len(fallback_text)
        
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
        
        # Add the actual task with structured response format
        user_content = f"""TEXT:
"{text}"

As a {daemon.name}, identify one specific issue or opportunity for improvement that ACTUALLY EXISTS in this text.

IMPORTANT: 
- Only identify issues that are actually present in the text. Do not make up or hallucinate problems that don't exist.
- If you cannot find any relevant issues in this text, respond with "No specific issues found in this text."
- Your question should be actionable and help the writer improve their work.
- Be specific about which exact text you're referring to in your suggestion.

RESPONSE FORMAT:
You must respond with a JSON object in this exact format:
{{
    "response": "your question or suggestion here",
    "text_to_highlight": "the exact text span that your question is about"
}}

The text_to_highlight should be the exact text from the original text that your question refers to.
- Copy the text exactly as it appears in the original text.
- If no specific span is relevant or no issues found, use "text_to_highlight": ""."""
        
        messages.append({"role": "user", "content": user_content})
        
        # Call OpenAI with structured output
        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=messages,
            max_tokens=200,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        response_content = response.choices[0].message.content.strip()
        
        try:
            parsed_response = json.loads(response_content)
            question = parsed_response.get("response", "")
            text_to_highlight = parsed_response.get("text_to_highlight", "")
            
            # Check if the AI found no issues
            if "no specific issues found" in question.lower():
                # Return empty span to indicate no highlighting needed
                return question, "", 0, 0
            
            # Find the text_to_highlight in the original text
            if text_to_highlight:
                start_index = text.find(text_to_highlight)
                if start_index != -1:
                    end_index = start_index + len(text_to_highlight)
                    span_text = text_to_highlight
                    print(f"DEBUG: Found text_to_highlight '{text_to_highlight}' at indices {start_index}-{end_index}")
                else:
                    print(f"DEBUG: Could not find text_to_highlight '{text_to_highlight}' in original text")
                    # Fallback to first sentence
                    end = text.find('.')
                    end = end + 1 if end != -1 else min(100, len(text))
                    span_text = text[:end].strip()
                    start_index = 0
                    end_index = end
                    print(f"DEBUG: Using fallback span: '{span_text}' at {start_index}-{end_index}")
            else:
                # No text to highlight, use fallback
                end = text.find('.')
                end = end + 1 if end != -1 else min(100, len(text))
                span_text = text[:end].strip()
                start_index = 0
                end_index = end
                print(f"DEBUG: No text_to_highlight provided, using fallback: '{span_text}' at {start_index}-{end_index}")
            
            print(f"DEBUG: Question: '{question}'")
            print(f"DEBUG: Final span: '{span_text}' at {start_index}-{end_index}")
            
            return question, span_text, start_index, end_index
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Raw response: {response_content}")
            # Fallback: treat the response as just a question
            question = response_content.strip()
            # Use simple fallback logic for span
            end = text.find('.')
            end = end + 1 if end != -1 else min(100, len(text))
            fallback_text = text[:end].strip()
            return question, fallback_text, 0, end
    
    except Exception as e:
        print(f"Error generating suggestion with span: {e}")
        fallback_question = f"[{daemon.name}] What could be improved in this section?"
        fallback_text = text[:100].strip()
        return fallback_question, fallback_text, 0, len(fallback_text)



def generate_answer(question: str, context: str, daemon: Daemon) -> str:
    """Generate an answer for a daemon's question."""
    try:
        if not client:
            return "OpenAI client not available. Please check API configuration."
        
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
            question, span_text, start_idx, end_idx = generate_suggestion_with_span(text, daemon)
            
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
        question, span_text, start_idx, end_idx = generate_suggestion_with_span(text, daemon)
        
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

def apply_suggestion_to_text(original_text: str, suggestion_question: str, span_text: Optional[str] = None, start_index: Optional[int] = None, end_index: Optional[int] = None, daemon_name: str = "") -> str:
    """Apply a suggestion to improve the given text using GPT-4.1."""
    try:
        if not client:
            raise Exception("OpenAI client not available. Please check API configuration.")

        # Build the prompt based on whether we have a specific span or not
        if span_text and start_index is not None and end_index is not None:
            # We have a specific span to focus on
            system_content = f"You are a helpful assistant that improves text based on suggestions from a {daemon_name}. You will apply the suggestion to the specified text span, making targeted improvements while preserving the overall structure and flow of the text."
            
            user_content = f"""ORIGINAL TEXT:
"{original_text}"

SUGGESTION FROM {daemon_name.upper()}:
"{suggestion_question}"

TEXT SPAN TO IMPROVE (characters {start_index}-{end_index}):
"{span_text}"

INSTRUCTIONS:
- Focus your improvements on the specified text span
- Apply the suggestion to make the text clearer, more accurate, or better structured
- Preserve the overall meaning and tone of the original text
- Return the complete improved text, not just the span
- Make sure the improved text flows naturally and maintains consistency with the rest of the content

Please provide the complete improved text:"""
        else:
            # No specific span, apply to entire text
            system_content = f"You are a helpful assistant that improves text based on suggestions from a {daemon_name}. You will apply the suggestion to improve the entire text while preserving its core meaning and structure."
            
            user_content = f"""ORIGINAL TEXT:
"{original_text}"

SUGGESTION FROM {daemon_name.upper()}:
"{suggestion_question}"

INSTRUCTIONS:
- Apply the suggestion to improve the entire text
- Make the text clearer, more accurate, or better structured based on the suggestion
- Preserve the overall meaning and tone of the original text
- Return the complete improved text

Please provide the complete improved text:"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-2025-04-14",
            messages=messages,
            max_tokens=1000,
            temperature=0.3
        )
        
        improved_text = response.choices[0].message.content.strip()
        
        # Remove any quotes that might have been added
        if improved_text.startswith('"') and improved_text.endswith('"'):
            improved_text = improved_text[1:-1]
        
        return improved_text
        
    except Exception as e:
        print(f"Error applying suggestion: {e}")
        raise Exception(f"Failed to apply suggestion: {str(e)}")

@app.post("/apply-suggestion")
def apply_suggestion_endpoint(request: ApplySuggestionRequest):
    """Apply a suggestion to improve the given text."""
    try:
        improved_text = apply_suggestion_to_text(
            original_text=request.original_text,
            suggestion_question=request.suggestion_question,
            span_text=request.span_text,
            start_index=request.start_index,
            end_index=request.end_index,
            daemon_name=request.daemon_name
        )
        return ApplySuggestionResponse(improved_text=improved_text)
    except Exception as e:
        print(f"Error in apply suggestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    try:
        return {
            "status": "healthy", 
            "daemons_count": len(daemons),
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "environment": "production" if os.getenv("VERCEL") else "development"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Daemon AI Backend...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🔑 Make sure OPENAI_API_KEY is set in your environment")
    print("-" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Vercel serverless function handler
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    # Fallback for local development
    handler = app
