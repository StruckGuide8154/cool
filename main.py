from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import jwt
import json
import hashlib
import time
from datetime import datetime, timedelta
import httpx
import logging
import os
from typing import Optional, Dict
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Depends, Request, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import jwt
import json
import hashlib
import time
from datetime import datetime, timedelta
import httpx
import logging
import os
import asyncio
import base64
import mimetypes
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import google.generativeai as genai
import anthropic
import numpy as np
from PIL import Image
import io
import av
from pathlib import Path


# Initialize
app = FastAPI()
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
security = HTTPBearer()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Enhanced Model Configurations
MODELS = {
    # Gemini Models
    "gemini-pro": {
        "input": 1.25*40, 
        "output": 5.00*40,
        "context_window": 1000000,
        "max_output_tokens": 2048,
        "features": ["text", "code", "vision", "audio"],
        "supports_stream": True
    },
    "gemini-pro-2": {
        "input": 2.50*40, 
        "output": 10.00*40,
        "context_window": 2000000,
        "max_output_tokens": 4096,
        "features": ["text", "code", "vision", "audio", "video"],
        "supports_stream": True
    },
    "gemini-flash": {
        "input": 0.075*40, 
        "output": 0.30*40,
        "context_window": 128000,
        "max_output_tokens": 2048,
        "features": ["text", "vision"],
        "supports_stream": True
    },

    # OpenAI Models
    "gpt4o": {
        "input": 0.0025*40, 
        "output": 0.00125*40,
        "context_window": 128000,
        "max_output_tokens": 16384,
        "features": ["text", "vision", "code"],
        "supports_stream": True
    },
    "gpt4o-mini": {
        "input": 0.00015*40, 
        "output": 0.000075*40,
        "context_window": 128000,
        "max_output_tokens": 16384,
        "features": ["text", "vision"],
        "supports_stream": True
    },

    # Claude Models
    "claude-haiku": {
        "input": 0.003*40, 
        "output": 0.00375*40,
        "context_window": 200000,
        "max_output_tokens": 4096,
        "features": ["text", "vision", "code"],
        "supports_stream": True
    },
    "claude-opus": {
        "input": 0.015*40, 
        "output": 0.075*40,
        "context_window": 200000,
        "max_output_tokens": 8192,
        "features": ["text", "vision", "code", "audio"],
        "supports_stream": True
    },
    "claude-sonnet": {
        "input": 0.008*40, 
        "output": 0.024*40,
        "context_window": 200000,
        "max_output_tokens": 8192,
        "features": ["text", "vision", "code"],
        "supports_stream": True
    }
}

# Initialize API clients
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "default-key"))
claude_client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY", "default-key"))

class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_tokens: Optional[int] = 0
    total_cost: float

class FileContent(BaseModel):
    mime_type: str
    data: str
    token_count: int

async def process_file(file: UploadFile) -> FileContent:
    """Process uploaded file and return content with token count"""
    content = await file.read()
    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]

    if mime_type.startswith('image/'):
        # Process image
        img = Image.open(io.BytesIO(content))
        width, height = img.size
        token_count = 258  # Base image token cost

        # Add resolution-based tokens
        token_count += (width * height) // (512 * 512) * 85

    elif mime_type.startswith('audio/'):
        # Process audio
        container = av.open(io.BytesIO(content))
        duration = float(container.duration) / av.time_base
        token_count = int(duration * 25)  # 25 tokens per second

    elif mime_type.startswith('video/'):
        # Process video
        container = av.open(io.BytesIO(content))
        duration = float(container.duration) / av.time_base
        token_count = int(duration * 300)  # 300 tokens per second includes frames/audio

    else:
        # Text and other files
        text_content = content.decode('utf-8', errors='ignore')
        token_count = len(text_content.split()) * 2  # Rough estimation

    return FileContent(
        mime_type=mime_type,
        data=base64.b64encode(content).decode(),
        token_count=token_count
    )

async def calculate_context_length(
    text: str,
    files: List[FileContent],
    chat_history: List[Dict] = None
) -> Dict[str, int]:
    """Calculate complete context length including history"""
    tokens = {
        "input_tokens": len(text.split()) * 2,  # Basic estimation
        "file_tokens": sum(f.token_count for f in files),
        "history_tokens": 0
    }

    if chat_history:
        for msg in chat_history:
            tokens["history_tokens"] += len(str(msg).split()) * 2

    tokens["total"] = sum(tokens.values())
    return tokens

@app.post("/api/ai/solve")
async def solve_with_model(
    request: Request,
    files: List[UploadFile] = File(None),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Main endpoint for model interaction with full feature support"""
    try:
        # Verify token and get user
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")

        # Parse request
        data = await request.json()
        model = data.get("model", "gpt4o-mini")
        content = data.get("text", "")
        stream = data.get("stream", False)
        chat_history = data.get("history", [])
        code_execution = data.get("code_execution", False)

        # Process files
        processed_files = []
        if files:
            processed_files = [await process_file(file) for file in files]

        # Calculate context length
        context = await calculate_context_length(content, processed_files, chat_history)

        # Check context window limits
        if context["total"] > MODELS[model]["context_window"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Context length {context['total']} exceeds model limit of {MODELS[model]['context_window']}"
            )

        # Calculate cost
        model_config = MODELS[model]
        cost = (
            (context["input_tokens"] + context["file_tokens"] + context["history_tokens"]) 
            * model_config["input"]
        ) + (context["total"] * 1.5 * model_config["output"])

        # Check credits
        if not user.get("is_free_tier") and user["credits"] < cost:
            raise HTTPException(status_code=402, detail="Insufficient credits")

        # Generate response based on model type
        if model.startswith("gpt"):
            response = await handle_openai(
                model, content, processed_files, stream, chat_history, code_execution
            )
        elif model.startswith("claude"):
            response = await handle_claude(
                model, content, processed_files, stream, chat_history, code_execution
            )
        else:
            response = await handle_gemini(
                model, content, processed_files, stream, chat_history, code_execution
            )

        # Update user credits and log usage
        if not user.get("is_free_tier"):
            user["credits"] -= cost
            update_user(user)

        log_usage(
            user["id"],
            model,
            context["total"],
            cost,
            len(content),
            len(processed_files)
        )

        if stream:
            return StreamingResponse(
                response,
                media_type="text/event-stream"
            )
        return response

    except Exception as e:
        logger.error(f"Error in solve_with_model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_openai(
    model: str,
    content: str,
    files: List[FileContent],
    stream: bool,
    history: List[Dict],
    code_execution: bool
):
    """Enhanced OpenAI handler with all features"""
    messages = []

    # Add history
    if history:
        messages.extend(history)

    # Add file contents
    for file in files:
        if file.mime_type.startswith(('image/', 'video/')):
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file.mime_type};base64,{file.data}"
                        }
                    }
                ]
            })

    # Add text content
    messages.append({"role": "user", "content": content})

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEYS['OPENAI']}"},
            json={
                "model": "gpt-4-vision-preview" if any(f.mime_type.startswith(('image/', 'video/')) for f in files) else model,
                "messages": messages,
                "stream": stream,
                "max_tokens": MODELS[model]["max_output_tokens"],
                "temperature": 0.7,
                "tools": [{"type": "code_interpreter"}] if code_execution else None
            }
        )

        if stream:
            return response.aiter_lines()

        return response.json()

async def handle_claude(
    model: str,
    content: str,
    files: List[FileContent],
    stream: bool,
    history: List[Dict],
    code_execution: bool
):
    """Enhanced Claude handler with all features"""
    messages = []

    # Add history
    if history:
        messages.extend(history)

    # Process files
    for file in files:
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": file.mime_type.split('/')[0],
                    "source": {
                        "type": "base64",
                        "media_type": file.mime_type,
                        "data": file.data
                    }
                }
            ]
        })

    # Add text content
    messages.append({
        "role": "user",
        "content": content
    })

    response = await claude_client.messages.create(
        model=model,
        max_tokens=MODELS[model]["max_output_tokens"],
        messages=messages,
        stream=stream,
        tools=[{"type": "code_interpreter"}] if code_execution else None
    )

    if stream:
        async for chunk in response:
            yield chunk
    else:
        return response

async def handle_gemini(
    model: str,
    content: str,
    files: List[FileContent],
    stream: bool,
    history: List[Dict],
    code_execution: bool
):
    """Enhanced Gemini handler with all features"""

    # Configure model
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": MODELS[model]["max_output_tokens"],
    }

    tools = None
    if code_execution:
        tools = ["code_execution"]

    genai_model = genai.GenerativeModel(
        model_name=f"gemini-{model}",
        generation_config=generation_config,
        tools=tools
    )

    # Start chat if history exists
    if history:
        chat = genai_model.start_chat(history=history)

    # Process contents
    contents = []
    for file in files:
        contents.append({
            "mime_type": file.mime_type,
            "data": file.data
        })

    # Add text content
    contents.append(content)

    # Generate response
    if history:
        response = await chat.send_message(
            contents,
            stream=stream
        )
    else:
        response = await genai_model.generate_content(
            contents,
            stream=stream
        )

    if stream:
        async for chunk in response:
            yield chunk
    else:
        return response.text

@app.post("/api/ai/upload")
async def upload_file(
    file: UploadFile = File(...),
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Handle file uploads with token counting"""
    try:
        processed_file = await process_file(file)
        return {
            "success": True,
            "file_info": {
                "name": file.filename,
                "type": processed_file.mime_type,
                "token_count": processed_file.token_count
            }
        }
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/models")
async def get_models(
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get available models and their capabilities"""
    return {
        "models": MODELS
    }

@app.get("/api/ai/usage/{user_id}")
async def get_user_usage(
    user_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get detailed usage statistics for a user"""
    try:
        payload = jwt.decode(auth.credentials,SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user or not user["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # Read usage from database
        with open(USAGE_FILE) as f:
            usage_data = json.load(f)
            user_usage = [item for item in usage_data["items"] if item["user_id"] == user_id]

        # Calculate aggregated statistics
        total_tokens = sum(item["tokens"] for item in user_usage)
        total_cost = sum(item["cost"] for item in user_usage)
        model_usage = {}

        for item in user_usage:
            model = item["model"]
            if model not in model_usage:
                model_usage[model] = {
                    "count": 0,
                    "tokens": 0,
                    "cost": 0.0
                }
            model_usage[model]["count"] += 1
            model_usage[model]["tokens"] += item["tokens"]
            model_usage[model]["cost"] += item["cost"]

        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "model_usage": model_usage,
            "detailed_usage": user_usage
        }

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def log_usage(user_id: str, model: str, tokens: int, cost: float, chars: int, files: int = 0):
    """Enhanced usage logging with file tracking"""
    with open(USAGE_FILE) as f:
        usage = json.load(f)

    usage["items"].append({
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "model": model,
        "tokens": tokens,
        "cost": cost,
        "chars": chars,
        "files_processed": files
    })

    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f)

@app.get("/api/ai/context_window/{model}")
async def get_context_window(
    model: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get context window information for a model"""
    try:
        if model not in MODELS:
            raise HTTPException(status_code=404, detail="Model not found")

        return {
            "model": model,
            "context_window": MODELS[model]["context_window"],
            "max_output_tokens": MODELS[model]["max_output_tokens"],
            "features": MODELS[model]["features"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/cache")
async def create_cache(
    request: Dict,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a context cache for large files/contexts"""
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")

        cache_id = f"cache_{user['id']}_{int(time.time())}"

        # Store in Redis with 1 hour expiration
        redis_client.setex(
            cache_id,
            3600,  # 1 hour
            json.dumps({
                "user_id": user["id"],
                "content": request.get("content", ""),
                "files": request.get("files", []),
                "created_at": datetime.utcnow().isoformat()
            })
        )

        return {
            "cache_id": cache_id,
            "expires_in": 3600
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/cache/{cache_id}")
async def get_cache(
    cache_id: str,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Retrieve cached content"""
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")

        cached = redis_client.get(cache_id)
        if not cached:
            raise HTTPException(status_code=404, detail="Cache not found")

        cached_data = json.loads(cached)
        if cached_data["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this cache")

        return cached_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Frontend helper components
@app.get("/components/ai-chat.js")
async def get_chat_component():
    """Serve the AI chat component"""
    return FileResponse(
        "static/components/ai-chat.js",
        media_type="application/javascript"
    )

@app.get("/components/file-upload.js")
async def get_file_upload_component():
    """Serve the file upload component"""
    return FileResponse(
        "static/components/file-upload.js",
        media_type="application/javascript"
    )


# Config
SECRET_KEY = "your-secret-key-change-in-production"
API_KEYS = {
    "OPENAI": os.environ.get("opene", "default-key"),  # Added default value
    "ANTHROPIC": os.environ.get("secretant", "default-key")  # Added default value
}
COSTS = {
    "gpt4o": {"input": 0.0025, "output": 0.00125},
    "gpt4o-mini": {"input": 0.00015, "output": 0.000075},
    "claude": {"input": 0.003, "output": 0.00375}
}

class LoginData(BaseModel):
    username: str
    password: str

class SolveRequest(BaseModel):
    text: str
    model: str = "gpt4o-mini"

class UpdateCreditsRequest(BaseModel):
    user_id: str
    amount: float

class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False

class ResetPasswordRequest(BaseModel):
    password: str

# Setup DB
os.makedirs("db", exist_ok=True)
USERS_FILE = "db/users.json"
USAGE_FILE = "db/usage.json"

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({"items": [
            {"id": "admin", "username": "admin", "password_hash": hashlib.sha256("admin123".encode()).hexdigest(), 
             "credits": 1000.0, "is_admin": True},
            {"id": "user", "username": "user", "password_hash": hashlib.sha256("user123".encode()).hexdigest(), 
             "credits": 100.0, "is_admin": False}
        ]}, f)

if not os.path.exists(USAGE_FILE):
    with open(USAGE_FILE, 'w') as f:
        json.dump({"items": []}, f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Helper functions
def get_user(username: str) -> Optional[Dict]:
    with open(USERS_FILE) as f:
        return next((u for u in json.load(f)["items"] if u["username"] == username), None)

def update_user(user: Dict):
    with open(USERS_FILE) as f:
        data = json.load(f)
    idx = next(i for i, u in enumerate(data["items"]) if u["id"] == user["id"])
    data["items"][idx] = user
    with open(USERS_FILE, 'w') as f:
        json.dump(data, f)

def calculate_cost(model: str, chars: int) -> float:
    cost = COSTS[model]
    return ((chars / 1000) * cost["input"] + (chars * 1.5 / 1000) * cost["output"]) * 5

# Routes
@app.get("/admin")
async def admin_ui():
    with open("templates/admin.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/login")
async def login(data: LoginData):
    user = get_user(data.username)
    if not user or user["password_hash"] != hashlib.sha256(data.password.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "token": jwt.encode({"user_id": user["id"], "exp": datetime.utcnow() + timedelta(days=1)}, SECRET_KEY),
        "user": {k: v for k, v in user.items() if k != "password_hash"}
    }


def compress_js(js_content):
    """
    Compress JavaScript by:
    1. Removing comments
    2. Removing unnecessary whitespace
    3. Minifying the code
    """
    # Remove single-line comments
    js_content = re.sub(r'//.*', '', js_content)

    # Remove multi-line comments
    js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)

    # Remove leading/trailing whitespace on each line
    js_content = '\n'.join(line.strip() for line in js_content.split('\n'))

    # Remove unnecessary whitespace between tokens
    js_content = re.sub(r'\s+', ' ', js_content)

    # Remove unnecessary spaces around operators and brackets
    js_content = re.sub(r'\s*([(){}\[\]=+\-*/])\s*', r'\1', js_content)

    # Remove newlines
    js_content = js_content.replace('\n', ' ')

    return js_content.strip()

@app.get("/exte", response_class=HTMLResponse)
async def question_solver_page():
    """
    Serves the Question Solver bookmarklet installation page
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Question Solver Bookmarklet</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            line-height: 1.6; 
        }
        h1 { color: #333; }
        .bookmarklet-button {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            cursor: move;
        }
        .instructions {
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <h1>Question Solver Bookmarklet</h1>

    <div class="instructions">
        <h2>Installation Steps:</h2>

        <h3>1. Show Bookmarks Bar</h3>
        <p>If your bookmarks bar is hidden:</p>
        <ul>
            <li>Chrome/Edge: Press Ctrl+Shift+B (Windows/Linux) or Cmd+Shift+B (Mac)</li>
            <li>Firefox: Press Ctrl+Shift+B (Windows/Linux) or Cmd+Shift+B (Mac)</li>
        </ul>

        <h3>2. Drag to Bookmarks Bar</h3>
        <p>Click and drag the button below to your bookmarks bar:</p>

        <a href="javascript:(function(){const s=document.createElement('script');s.src='https://5b7a0633-a297-4047-b0ee-a4bde446805d-00-1ntphoomm251x.kirk.replit.dev/script.js';document.body.appendChild(s);})();" class="bookmarklet-button">Question Solver</a>

        <h3>3. Use the Bookmarklet</h3>
        <p>Click the "Question Solver" bookmark on any webpage to activate</p>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/script.js")
async def get_script():
    return FileResponse("script.js", media_type="application/javascript")



@app.post("/api/admin/users/{user_id}/reset_password")
async def reset_password(user_id: str, request: ResetPasswordRequest, auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        admin = get_user(payload["user_id"])
        if not admin or not admin["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        with open(USERS_FILE, 'r+') as f:
            data = json.load(f)
            user = next((u for u in data["items"] if u["id"] == user_id), None)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user["password_hash"] = hashlib.sha256(request.password.encode()).hexdigest()
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

        return {"message": "Password reset successfully"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        admin = get_user(payload["user_id"])
        if not admin or not admin["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        with open(USERS_FILE, 'r+') as f:
            data = json.load(f)
            data["items"] = [user for user in data["items"] if user["id"] != user_id]
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

        return {"message": "User deleted successfully"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
@app.post("/api/admin/users")
async def create_user(request: CreateUserRequest, auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        admin = get_user(payload["user_id"])
        if not admin or not admin["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        new_user = {
            "id": request.username,
            "username": request.username,
            "password_hash": hashlib.sha256(request.password.encode()).hexdigest(),
            "credits": 0.0,
            "is_admin": request.is_admin
        }

        with open(USERS_FILE, 'r+') as f:
            data = json.load(f)
            data["items"].append(new_user)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

        return {"message": "User created successfully"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/api/solve")
async def solve_question(request: SolveRequest, auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # Verify token and get user
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")

        # Calculate cost
        cost = calculate_cost(request.model, len(request.text))

        # Check credits if not free tier
        if not user.get("is_free_tier") and user["credits"] < cost:
            raise HTTPException(status_code=402, detail="Insufficient credits")

        # Make API request based on model
        if request.model.startswith("gpt"):
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {API_KEYS['OPENAI']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-turbo-preview" if request.model == "gpt4o" else "gpt-3.5-turbo",
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an expert at answering questions. Provide your response as a valid JSON object with exactly these three fields: 'answer' (a concise answer), 'explanation' (a brief explanation), and 'confidence' (a number 0-100). Example: {\"answer\": \"ampere\", \"explanation\": \"Current is measured in amperes (A)\", \"confidence\": 95}"
                            },
                            {
                                "role": "user",
                                "content": request.text
                            }
                        ]
                    }
                )

                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="OpenAI API error")

                response_content = response.json()["choices"][0]["message"]["content"]
                try:
                    # Handle both string and dict responses
                    if isinstance(response_content, dict):
                        result = response_content
                    else:
                        # Remove any potential leading/trailing whitespace
                        response_content = response_content.strip()
                        # Parse the string response
                        result = json.loads(response_content)

                    # Ensure required fields exist
                    if not all(key in result for key in ['answer', 'explanation', 'confidence']):
                        raise ValueError("Missing required fields in response")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GPT response: {response_content}")
                    result = {
                        "answer": "Error parsing response",
                        "explanation": "The model returned an invalid format",
                        "confidence": 0
                    }

        else:  # Claude
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": API_KEYS["ANTHROPIC"],
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-sonnet-20240229",
                        "max_tokens": 150,
                        "messages": [{
                            "role": "user",
                            "content": f"Answer this question and format the response exactly like this example, nothing else: {{'answer': 'ampere', 'explanation': 'Current is measured in amperes (A)', 'confidence': 95}}\n\nQuestion: {request.text}"
                        }]
                    }
                )

                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="Anthropic API error")

                response_content = response.json()["content"][0]["text"]
                try:
                    # Handle both string and dict responses
                    if isinstance(response_content, dict):
                        result = response_content
                    else:
                        # Remove any potential leading/trailing whitespace
                        response_content = response_content.strip()
                        # Parse the string response
                        result = json.loads(response_content)

                    # Ensure required fields exist
                    if not all(key in result for key in ['answer', 'explanation', 'confidence']):
                        raise ValueError("Missing required fields in response")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Claude response: {response_content}")
                    result = {
                        "answer": "Error parsing response",
                        "explanation": "The model returned an invalid format",
                        "confidence": 0
                    }

        # Deduct credits if not free tier
        if not user.get("is_free_tier"):
            user["credits"] -= cost
            update_user(user)

        # Log usage
        with open(USAGE_FILE) as f:
            usage = json.load(f)
        usage["items"].append({
            "user_id": user["id"],
            "timestamp": datetime.utcnow().isoformat(),
            "model": request.model,
            "cost": cost,
            "chars": len(request.text)
        })
        with open(USAGE_FILE, "w") as f:
            json.dump(usage, f)

        return {
            "response": result,
            "cost": cost,
            "cached": False
        }

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error in solve_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/users/{user_id}/usage")
async def get_user_usage(user_id: str, auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        admin = get_user(payload["user_id"])
        if not admin or not admin["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        with open(USAGE_FILE) as f:
            usage_data = json.load(f)
            user_usage = [item for item in usage_data["items"] if item["user_id"] == user_id]

        return user_usage
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
@app.get("/api/admin/users")
async def get_users(auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user or not user["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        with open(USERS_FILE) as f:
            return json.load(f)["items"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/admin/usage")
async def get_usage(auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user or not user["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        with open(USAGE_FILE) as f:
            return json.load(f)["items"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/admin/update_credits")
async def update_user_credits(request: UpdateCreditsRequest, auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        admin = get_user(payload["user_id"])
        if not admin or not admin["is_admin"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        user = get_user(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user["credits"] += request.amount
        update_user(user)
        return {"message": "Credits updated successfully"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Add verification endpoint
@app.get("/api/verify")
async def verify_token(auth: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=["HS256"])
        user = get_user(payload["user_id"])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid user")
        return {"valid": True}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)  # Changed port to 80