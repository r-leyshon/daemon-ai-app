import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import uuid
from dotenv import load_dotenv
import pathlib
from config import get_cors_origins

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

# Load environment variables from .env file in project root (for local development)
# Go up from backend/main.py to project root
project_root = pathlib.Path(__file__).parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Vertex AI Configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "europe-west1")  # Belgium - closest to UK with model availability
VERTEX_MODEL = os.getenv("VERTEX_MODEL", "gemini-2.0-flash")  # Confirmed working model

# Handle service account credentials
# For local development: use GOOGLE_APPLICATION_CREDENTIALS env var or vertex-key.json
# For Vercel: use base64-encoded credentials in GOOGLE_APPLICATION_CREDENTIALS_JSON
backend_dir = pathlib.Path(__file__).parent
local_key_path = backend_dir / "vertex-key.json"

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    # Vercel deployment: decode base64 credentials and write to temp file
    import base64
    import tempfile
    try:
        credentials_content = base64.b64decode(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='wb')
        temp_file.write(credentials_content)
        temp_file.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
        print("✅ Loaded credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON")
    except Exception as e:
        print(f"❌ Error decoding GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
elif local_key_path.exists():
    # Local development: use the vertex-key.json file
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(local_key_path)
    print(f"✅ Using local credentials from {local_key_path}")

# Debug: Check if GCP Project is configured
if not GCP_PROJECT_ID:
    print("❌ ERROR: GCP_PROJECT_ID not found in environment variables")
    print(f"Project root: {project_root}")
    print(f"Looking for .env file at: {env_path}")
    print(f"File exists: {env_path.exists()}")
    # Don't exit in production, just log the error
    if os.getenv("VERCEL") is None:
        exit(1)
else:
    print(f"✅ GCP Project ID: {GCP_PROJECT_ID}")
    print(f"✅ GCP Location: {GCP_LOCATION}")
    print(f"✅ Using model: {VERTEX_MODEL}")

# Initialize Vertex AI
model = None
try:
    if GCP_PROJECT_ID:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        model = GenerativeModel(VERTEX_MODEL)
        print("✅ Vertex AI initialized successfully")
    else:
        print("⚠️ GCP Project ID not found, model not initialized")
except Exception as e:
    print(f"❌ Error initializing Vertex AI: {e}")
    model = None

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
    # Optional inline daemon config for custom (session-only) daemons
    daemon_config: Optional[Dict] = None

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
    suggested_fix: Optional[str] = None
    is_outdated: bool = False

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



def generate_suggestion_with_span(text: str, daemon: Daemon) -> tuple[str, str, int, int, str]:
    """Generate a suggestion/question with text span information in a single API call."""
    try:
        if not model:
            # Fallback when model is not available
            fallback_question = f"[{daemon.name}] Vertex AI not available. Please check GCP configuration."
            fallback_text = text[:100].strip()
            return fallback_question, fallback_text, 0, len(fallback_text), ""
        
        # Build the prompt for Gemini
        system_prompt = f"{daemon.prompt} {daemon.guardrails or ''}"
        
        # Add examples if available
        examples_text = ""
        for example in daemon.examples:
            examples_text += f"\nUser: {example['user']}\nAssistant: {example['assistant']}\n"
        
        # Check if this is a default "issue-finding" daemon or a custom daemon
        default_daemon_ids = {"devil_advocate", "grammar_enthusiast", "clarity_coach"}
        is_default_daemon = daemon.id in default_daemon_ids
        
        if is_default_daemon:
            task_instruction = f"""As a {daemon.name}, identify one specific issue or opportunity for improvement in this text."""
        else:
            task_instruction = f"""Apply your role as "{daemon.name}" to analyze this text according to your purpose: {daemon.prompt}"""
        
        # Simple prompt that asks for JSON response
        full_prompt = f"""{system_prompt}
{examples_text}

TEXT TO ANALYZE:
"{text}"

{task_instruction}

You MUST respond with ONLY a JSON object in this exact format (no other text):
{{"response": "your suggestion or question", "text_to_highlight": "exact quote from text above", "suggested_fix": "your improved version"}}"""
        
        # Call Vertex AI
        generation_config = GenerationConfig(
            max_output_tokens=800,
            temperature=0.7
        )
        
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        # Get response text
        response_text = response.text
        if not response_text:
            raise Exception("Empty response from Gemini")
        
        # Clean up and parse JSON
        response_content = response_text.strip()
        
        # Remove markdown code blocks if present (handle various formats)
        import re as regex
        # Remove ```json ... ``` blocks
        code_block_match = regex.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_content, regex.DOTALL)
        if code_block_match:
            response_content = code_block_match.group(1)
        else:
            # Try simple stripping
            if response_content.startswith("```json"):
                response_content = response_content[7:]
            elif response_content.startswith("```"):
                response_content = response_content[3:]
            if response_content.endswith("```"):
                response_content = response_content[:-3]
            response_content = response_content.strip()
        
        # Find JSON in response
        json_start = response_content.find("{")
        json_end = response_content.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            response_content = response_content[json_start:json_end]
        
        try:
            parsed_response = json.loads(response_content)
        except json.JSONDecodeError:
            # JSON parse failed - try to extract just the response field with regex
            response_match = regex.search(r'"response"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', response_text)
            if response_match:
                parsed_response = {
                    "response": response_match.group(1).replace('\\"', '"'),
                    "text_to_highlight": "",
                    "suggested_fix": ""
                }
            else:
                # Final fallback - clean up raw text
                clean_text = response_text.replace("```json", "").replace("```", "").strip()
                parsed_response = {
                    "response": clean_text[:300] if clean_text else "Could not generate suggestion",
                    "text_to_highlight": "",
                    "suggested_fix": ""
                }
        
        # Extract fields from parsed response
        question = parsed_response.get("response", "")
        text_to_highlight = parsed_response.get("text_to_highlight", "")
        suggested_fix = parsed_response.get("suggested_fix", "")
        
        # Check if the AI found no issues
        if "no specific issues found" in question.lower():
            return question, "", 0, 0, ""
        
        # Find the text_to_highlight in the original text
        if text_to_highlight:
            start_index = text.find(text_to_highlight)
            if start_index != -1:
                end_index = start_index + len(text_to_highlight)
                span_text = text_to_highlight
            else:
                # Fallback to first sentence
                end = text.find('.')
                end = end + 1 if end != -1 else min(100, len(text))
                span_text = text[:end].strip()
                start_index = 0
                end_index = end
        else:
            # No text to highlight, use fallback
            end = text.find('.')
            end = end + 1 if end != -1 else min(100, len(text))
            span_text = text[:end].strip()
            start_index = 0
            end_index = end
        
        return question, span_text, start_index, end_index, suggested_fix
    
    except Exception as e:
        print(f"Error generating suggestion with span: {e}")
        fallback_question = f"[{daemon.name}] What could be improved in this section?"
        fallback_text = text[:100].strip()
        return fallback_question, fallback_text, 0, len(fallback_text), ""


# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Daemon AI Backend is running"}

@app.get("/daemons")
def list_daemons():
    """Get all available daemons."""
    return {"daemons": list(daemons.values())}

# Note: Custom daemons are now session-only (stored in browser, not on server).
# These endpoints are kept for backward compatibility but custom daemons 
# should be handled entirely in the frontend using sessionStorage.

@app.post("/daemons")
def add_daemon(daemon: Daemon):
    """Validate a custom daemon config (but don't store it on the server).
    
    Custom daemons are now session-only - they should be stored in the 
    browser's sessionStorage, not on the server. This endpoint validates 
    the daemon config and returns it with a generated ID.
    """
    daemon_id = daemon.id or f"custom_{uuid.uuid4()}"
    daemon.id = daemon_id
    # Don't store on server - just validate and return
    return {"id": daemon_id, "status": "validated", "daemon": daemon, "session_only": True}

@app.delete("/daemons/{daemon_id}")
def delete_daemon(daemon_id: str):
    """Delete endpoint - only works for default daemons (which cannot be deleted).
    
    Custom daemons are session-only and managed in the browser.
    """
    default_daemon_ids = {"devil_advocate", "grammar_enthusiast", "clarity_coach"}
    
    if daemon_id in default_daemon_ids:
        raise HTTPException(status_code=400, detail="Cannot delete default daemons")
    
    # Custom daemons are not stored on the server
    # Return success since the daemon doesn't exist on server anyway
    return {"id": daemon_id, "status": "not_found_on_server", "message": "Custom daemons are session-only and managed in the browser"}


@app.post("/suggestion/{daemon_id}")
def get_suggestion_from_daemon(daemon_id: str, input_data: TextInput):
    """Generate a suggestion for the given text from a specific daemon.
    
    For default daemons: looks up daemon by ID from server storage.
    For custom daemons: uses inline daemon_config from request body (session-only, not stored).
    """
    # Check if this is a custom daemon with inline config
    if input_data.daemon_config:
        # Use inline config for custom (session-only) daemons
        try:
            daemon = Daemon(
                id=daemon_id,
                name=input_data.daemon_config.get("name", "Custom Daemon"),
                prompt=input_data.daemon_config.get("prompt", ""),
                examples=input_data.daemon_config.get("examples", []),
                guardrails=input_data.daemon_config.get("guardrails"),
                color=input_data.daemon_config.get("color", "#f39c12")
            )
            print(f"Using inline daemon config for custom daemon: {daemon.name}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid daemon config: {str(e)}")
    else:
        # Look up default daemon from server storage
        daemon = daemons.get(daemon_id)
        if not daemon:
            raise HTTPException(status_code=404, detail="Daemon not found")
    
    text = input_data.text
    
    try:
        print(f"Processing text with {daemon.name}: {text[:100]}...")  # Debug log
        question, span_text, start_idx, end_idx, suggested_fix = generate_suggestion_with_span(text, daemon)
        
        suggestion = Suggestion(
            daemon_id=daemon_id,
            daemon_name=daemon.name,
            question=question,
            span_text=span_text,
            start_index=start_idx,
            end_index=end_idx,
            color=daemon.color,
            suggested_fix=suggested_fix
        )
        
        print(f"Generated suggestion: {question}")  # Debug log
        print(f"Span text: '{span_text}', start: {start_idx}, end: {end_idx}")  # Debug log
        return {"suggestion": suggestion}
        
    except Exception as e:
        print(f"Error processing daemon {daemon_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestion: {str(e)}")


def apply_suggestion_to_text(original_text: str, suggestion_question: str, span_text: Optional[str] = None, start_index: Optional[int] = None, end_index: Optional[int] = None, daemon_name: str = "") -> str:
    """Apply a suggestion to improve the given text using Gemini."""
    try:
        if not model:
            raise Exception("Vertex AI not available. Please check GCP configuration.")

        # Build the prompt based on whether we have a specific span or not
        if span_text and start_index is not None and end_index is not None:
            # We have a specific span to focus on
            full_prompt = f"""You are a helpful assistant that improves text based on suggestions from a {daemon_name}. 

ORIGINAL TEXT:
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
            full_prompt = f"""You are a helpful assistant that improves text based on suggestions from a {daemon_name}.

ORIGINAL TEXT:
"{original_text}"

SUGGESTION FROM {daemon_name.upper()}:
"{suggestion_question}"

INSTRUCTIONS:
- Apply the suggestion to improve the entire text
- Make the text clearer, more accurate, or better structured based on the suggestion
- Preserve the overall meaning and tone of the original text
- Return the complete improved text

Please provide the complete improved text:"""

        generation_config = GenerationConfig(
            max_output_tokens=1000,
            temperature=0.3
        )
        
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        # Get text from response
        if response.text:
            improved_text = response.text.strip()
        else:
            raise Exception("Empty response from Gemini")
        
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
            "gcp_project_configured": bool(GCP_PROJECT_ID),
            "model_initialized": bool(model),
            "gcp_location": GCP_LOCATION,
            "model": VERTEX_MODEL,
            "environment": "production" if os.getenv("VERCEL") else "development"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Daemon AI Backend...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🔑 Make sure GCP_PROJECT_ID is set in your environment")
    print(f"🌍 Using Vertex AI in region: {GCP_LOCATION}")
    print(f"🤖 Model: {VERTEX_MODEL}")
    print("-" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Vercel serverless function handler
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    # Fallback for local development
    handler = app
