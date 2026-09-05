# Vertex AI Integration Learnings

Lessons learned from migrating from Azure OpenAI to Google Cloud Vertex AI with Gemini models.

---

## 1. GCP Setup Checklist

### Required APIs
Enable these in Google Cloud Console → APIs & Services:
- **Vertex AI API** (required)
- **Generative Language API** (required for Gemini models)

### Service Account Setup
1. Create service account: IAM & Admin → Service Accounts → Create
2. Required IAM roles:
   - `Vertex AI User`
   - `Service Usage Consumer`
3. Create JSON key: Keys → Add Key → Create new key → JSON
4. **Never commit the key file** - add to `.gitignore`

### Authentication in Code
```python
import os
import pathlib

# Local development: use key file
local_key_path = pathlib.Path(__file__).parent / "vertex-key.json"
if local_key_path.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(local_key_path)

# Production (Vercel/Cloud): use base64-encoded credentials
elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    import base64
    import tempfile
    credentials = base64.b64decode(os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON"))
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='wb')
    temp_file.write(credentials)
    temp_file.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
```

---

## 2. Model Availability by Region

**Key insight**: Not all Gemini models are available in all regions. Models can be deprecated!

| Model | us-central1 | europe-west1 | europe-west2 (London) | Status |
|-------|-------------|--------------|----------------------|--------|
| gemini-3.5-flash | ✅ | ✅ | ✅ | Current |
| gemini-2.5-flash | ✅ | ✅ | ✅ | Current |
| gemini-2.0-flash | ❌ | ❌ | ❌ | **Deprecated June 2026** |
| gemini-1.5-pro | ✅ | ✅ | ❌ | Legacy |
| gemini-1.5-flash | ✅ | ✅ | ❌ | Legacy |

**Recommendation**: Use `europe-west2` (London) for UK-based apps - has newer model availability and lower latency.

### Diagnostic Script
```python
import vertexai
from vertexai.generative_models import GenerativeModel

def test_model(region, model_name):
    try:
        vertexai.init(project="your-project", location=region)
        model = GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"✅ {region} / {model_name}: {response.text[:50]}")
    except Exception as e:
        print(f"❌ {region} / {model_name}: {str(e)[:50]}")

# Test availability for current models
for region in ["us-central1", "europe-west1", "europe-west2"]:
    for model in ["gemini-3.5-flash", "gemini-2.5-flash"]:
        test_model(region, model)
```

---

## 3. Getting Reliable Structured JSON Output

### The Problem
Simply prompting "return JSON" doesn't work reliably. Models may:
- Prefix with "Here is the JSON..."
- Wrap in markdown code blocks
- Return truncated/incomplete JSON
- Omit required fields

### The Solution: JSON Schema Enforcement

```python
from vertexai.generative_models import GenerativeModel, GenerationConfig

# Define the schema
response_schema = {
    "type": "object",
    "properties": {
        "response": {"type": "string", "description": "Your feedback"},
        "text_to_highlight": {"type": "string", "description": "Text to highlight"},
        "suggested_fix": {"type": "string", "description": "Improved version"}
    },
    "required": ["response", "text_to_highlight", "suggested_fix"]
}

# Use schema with JSON mime type
generation_config = GenerationConfig(
    max_output_tokens=2048,  # Generous limit to prevent truncation
    temperature=0.7,
    response_mime_type="application/json",  # Forces JSON output
    response_schema=response_schema  # Enforces structure
)

response = model.generate_content(prompt, generation_config=generation_config)
```

### Key Points
- `response_mime_type="application/json"` forces JSON (no markdown wrappers)
- `response_schema` enforces field names and types
- Use `"required": [...]` to ensure all fields are returned
- Pass a dict schema, NOT a Pydantic class (causes `ModelMetaclass` error)

---

## 4. Handling Truncated Responses

Even with schemas, responses may be truncated. Add robust extraction:

```python
import json
import re

def parse_llm_response(response_text: str) -> dict:
    """Parse LLM response, handling truncation gracefully."""
    
    # Try standard JSON parsing first
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    
    # Fallback: extract fields from truncated JSON
    def extract_field(text: str, field: str) -> str:
        pattern = rf'"{field}"\s*:\s*"'
        match = re.search(pattern, text)
        if not match:
            return ""
        start = match.end()
        result = []
        i = start
        while i < len(text):
            if text[i] == '"' and (i == start or text[i-1] != '\\'):
                break
            if text[i] == '\\' and i + 1 < len(text):
                result.append(text[i+1])
                i += 2
            else:
                result.append(text[i])
                i += 1
        return ''.join(result).strip()
    
    return {
        "response": extract_field(response_text, "response"),
        "text_to_highlight": extract_field(response_text, "text_to_highlight"),
        "suggested_fix": extract_field(response_text, "suggested_fix")
    }
```

---

## 5. Avoid Redundant Model Calls

### The Problem
Calling the model again to "apply" a suggestion when you already have the fix is wasteful and can cause truncation.

### The Solution
If you already have the suggested text, use direct string replacement:

```python
def apply_fix(original_text: str, span_text: str, suggested_fix: str) -> str:
    """Apply a fix using direct replacement - no model call needed."""
    if suggested_fix and span_text and span_text in original_text:
        return original_text.replace(span_text, suggested_fix, 1)
    
    # Only fall back to model if we don't have what we need
    return call_model_to_apply(original_text, span_text)
```

---

## 6. Environment Variables

### Local Development (`.env`)
```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=europe-west2
VERTEX_MODEL=gemini-3.5-flash
```

### Production (Vercel)
```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=europe-west2
VERTEX_MODEL=gemini-3.5-flash
GOOGLE_APPLICATION_CREDENTIALS_JSON=<base64-encoded-service-account-key>
```

Generate base64 key:
```bash
base64 -i vertex-key.json | tr -d '\n'
```

---

## 7. Dependencies

```
google-cloud-aiplatform>=1.74.0
```

This single package includes `vertexai` and all required dependencies.

---

## 8. Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `404 Publisher Model not found` | Wrong region, model name, or deprecated model | Check model availability; use fallback logic |
| `invalid_scope` | Missing API enablement | Enable Vertex AI API and Generative Language API |
| `ModelMetaclass is not iterable` | Passing Pydantic class to response_schema | Use dict schema instead |
| Truncated JSON | Token limit too low | Increase `max_output_tokens` |
| Raw JSON in output | Schema not enforced | Add `response_mime_type` AND `response_schema` |
| Model suddenly stops working | Model deprecated (e.g., gemini-2.0-flash June 2026) | Implement model fallback logic |

### Model Fallback Pattern

To handle model deprecations gracefully:

```python
MODEL_FALLBACK_ORDER = ['gemini-3.5-flash', 'gemini-2.5-flash']

def call_with_fallback(operation_func, preferred_model=None):
    """Execute an AI operation with automatic model fallback on 404 errors."""
    models_to_try = [preferred_model] if preferred_model else []
    models_to_try.extend([m for m in MODEL_FALLBACK_ORDER if m != preferred_model])
    
    last_error = None
    for model_id in models_to_try:
        try:
            return operation_func(model_id)
        except Exception as e:
            last_error = e
            if hasattr(e, 'status_code') and e.status_code == 404:
                print(f"Model {model_id} not available, trying next...")
                continue
            raise  # Re-raise non-404 errors immediately
    
    raise last_error  # All models failed
```

---

## Quick Start Template

```python
import json
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig

# Model fallback configuration
MODEL_FALLBACK_ORDER = ['gemini-3.5-flash', 'gemini-2.5-flash']

# Initialize
vertexai.init(project="your-project", location="europe-west2")

def get_model_with_fallback(preferred_model='gemini-3.5-flash'):
    """Initialize model with fallback support."""
    models_to_try = [preferred_model] + [m for m in MODEL_FALLBACK_ORDER if m != preferred_model]
    for model_id in models_to_try:
        try:
            return GenerativeModel(model_id), model_id
        except Exception as e:
            if '404' in str(e).lower():
                print(f"Model {model_id} not available, trying next...")
                continue
            raise
    raise Exception("All models unavailable")

model, active_model = get_model_with_fallback()
print(f"Using model: {active_model}")

# Define schema
schema = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "number"}
    },
    "required": ["answer", "confidence"]
}

# Generate with structured output
config = GenerationConfig(
    max_output_tokens=2048,
    temperature=0.7,
    response_mime_type="application/json",
    response_schema=schema
)

response = model.generate_content("What is 2+2?", generation_config=config)
result = json.loads(response.text)
print(result)  # {"answer": "4", "confidence": 1.0}
```
