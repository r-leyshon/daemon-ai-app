import os
import json
from http.server import BaseHTTPRequestHandler
from typing import List, Dict, Optional
import re
import uuid

# Import the full FastAPI app and functions from main.py
from main import app, daemons, generate_suggestion_for_daemon, find_text_span, generate_answer, Daemon, TextInput, Suggestion, AnswerRequest, AnswerResponse

# Initialize OpenAI client (imported from main.py)
from main import client, api_key

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Handle GET requests
        if self.path == "/health":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "daemons_count": len(daemons),
                "api_key_configured": bool(api_key),
                "client_initialized": client is not None,
                "environment": "production" if os.getenv("VERCEL") else "development"
            }
            
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
        
        elif self.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response = {"message": "Daemon AI Backend is running"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
        
        elif self.path == "/daemons":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {"daemons": list(daemons.values())}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
        
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
    
    def do_POST(self):
        # Handle suggestion requests
        if self.path.startswith("/suggestion/"):
            try:
                # Parse the request body
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                text = request_data.get('text', '')
                daemon_id = self.path.split('/')[-1]
                
                daemon = daemons.get(daemon_id)
                if not daemon:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Daemon not found"}).encode('utf-8'))
                    return
                
                # Use the full AI-powered suggestion logic
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
                
                response_data = {"suggestion": suggestion.dict()}
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {"error": str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
        
        # Handle add daemon requests
        elif self.path == "/daemons":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                daemon_id = request_data.get('id') or str(uuid.uuid4())
                daemon = Daemon(
                    id=daemon_id,
                    name=request_data.get('name'),
                    prompt=request_data.get('prompt'),
                    guardrails=request_data.get('guardrails'),
                    color=request_data.get('color'),
                    examples=request_data.get('examples', [])
                )
                
                daemons[daemon_id] = daemon
                
                response_data = {"id": daemon_id, "status": "added", "daemon": daemon.dict()}
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {"error": str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
        
        # Handle answer requests
        elif self.path == "/answer":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                daemon = daemons.get(request_data.get('daemon_id'))
                if not daemon:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Daemon not found"}).encode('utf-8'))
                    return
                
                answer = generate_answer(
                    request_data.get('question'),
                    request_data.get('span_text'),
                    daemon
                )
                
                response_data = {
                    "daemon_id": request_data.get('daemon_id'),
                    "question": request_data.get('question'),
                    "answer": answer
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                return
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {"error": str(e)}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
                return
        
        # Handle other POST requests
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {"error": "Endpoint not found"}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return 