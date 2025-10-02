"""
Simple FastAPI backend for RAG application login.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="RAG Assistant API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage
users_db = {
    "admin@example.com": {
        "id": "1",
        "username": "admin",
        "email": "admin@example.com",
        "password": "password",  # In production, this would be hashed
        "is_admin": True,
        "created_at": "2024-01-01T00:00:00Z"
    }
}

workspaces_db = {
    "1": {
        "id": "1",
        "name": "Demo Workspace",
        "description": "A demo workspace for testing",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "member_count": 1,
        "data_source_count": 0,
        "is_active": True,
        "role": "admin"
    }
}

SECRET_KEY = "your-secret-key-here"

# Pydantic models
class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class User(BaseModel):
    id: str
    username: str
    email: str
    is_admin: bool
    created_at: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User

class Workspace(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    member_count: int
    data_source_count: int

def create_token(user_data: dict) -> str:
    """Create JWT token for user."""
    payload = {
        "user_id": user_data["id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "is_admin": user_data["is_admin"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# Routes
@app.get("/")
async def root():
    return {"message": "RAG Assistant API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": True,
        "vector_store": True,
        "llm_service": True,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """User login endpoint."""
    # Get login identifier (username or email)
    login_identifier = request.username or request.email
    if not login_identifier:
        raise HTTPException(status_code=400, detail="Username or email is required")
    
    # Find user by username or email
    user_data = None
    for email, user in users_db.items():
        if user["username"] == login_identifier or user["email"] == login_identifier:
            user_data = user
            break
    
    if not user_data or user_data["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_token(user_data)
    
    # Return user data
    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        is_admin=user_data["is_admin"],
        created_at=user_data["created_at"]
    )
    
    return AuthResponse(
        access_token=token,
        user=user
    )

@app.post("/api/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """User registration endpoint."""
    # Check if user already exists
    for email, user in users_db.items():
        if user["email"] == request.email or user["username"] == request.username:
            raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    user_id = str(len(users_db) + 1)
    user_data = {
        "id": user_id,
        "username": request.username,
        "email": request.email,
        "password": request.password,  # In production, hash this
        "is_admin": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    users_db[request.email] = user_data
    
    # Create token
    token = create_token(user_data)
    
    # Return user data
    user = User(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        is_admin=user_data["is_admin"],
        created_at=user_data["created_at"]
    )
    
    return AuthResponse(
        access_token=token,
        user=user
    )

@app.get("/api/auth/me")
async def get_current_user(authorization: str = Depends(lambda: None)):
    """Get current user info."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "success": True,
        "user": {
            "id": payload["user_id"],
            "username": payload["username"],
            "email": payload["email"],
            "is_admin": payload["is_admin"]
        }
    }

@app.get("/api/workspaces")
async def get_workspaces():
    """Get user workspaces."""
    return list(workspaces_db.values())

@app.get("/api/workspaces/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace details."""
    if workspace_id not in workspaces_db:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    return {
        "success": True,
        "workspace": workspaces_db[workspace_id]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
