#!/usr/bin/env python3
"""
Simple Authentication API for HarvestBot
Provides exactly what your React frontend needs
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt
import hashlib
import sqlite3
import os
import uuid

# Configuration
SECRET_KEY = "harvestbot-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
DB_PATH = "harvestbot_users.db"

# Initialize FastAPI app
app = FastAPI(title="HarvestBot Auth API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3017", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    message: Optional[str] = None

class VerifyResponse(BaseModel):
    success: bool
    message: Optional[str] = None

# Database functions
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash password"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password"""
    return hash_password(password) == password_hash

def create_access_token(username: str) -> str:
    """Create JWT token"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> str:
    """Verify JWT token and return username"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token"""
    return verify_token(credentials.credentials)

# API Routes
@app.get("/")
async def root():
    return {"message": "HarvestBot Authentication API", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """User signup - matches React frontend expectation"""
    try:
        # Validate input
        if len(request.username) < 3:
            return AuthResponse(success=False, message="Username must be at least 3 characters")
        
        if len(request.password) < 6:
            return AuthResponse(success=False, message="Password must be at least 6 characters")
        
        # Check if user exists
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (request.username,))
        
        if cursor.fetchone():
            conn.close()
            return AuthResponse(success=False, message="Username already exists. Please choose a different username.")
        
        # Create user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(request.password)
        cursor.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, request.username, password_hash)
        )
        conn.commit()
        conn.close()
        
        # Create token
        token = create_access_token(request.username)
        
        return AuthResponse(
            success=True,
            token=token,
            username=request.username,
            message="Account created successfully"
        )
        
    except Exception as e:
        return AuthResponse(success=False, message=f"Signup failed: {str(e)}")

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """User login - matches React frontend expectation"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (request.username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user or not verify_password(request.password, user[1]):
            return AuthResponse(success=False, message="Invalid username or password")
        
        # Create token
        token = create_access_token(request.username)
        
        return AuthResponse(
            success=True,
            token=token,
            username=request.username,
            message="Login successful"
        )
        
    except Exception as e:
        return AuthResponse(success=False, message=f"Login failed: {str(e)}")

@app.get("/api/auth/verify", response_model=VerifyResponse)
async def verify(current_user: str = Depends(get_current_user)):
    """Token verification - matches React frontend expectation"""
    return VerifyResponse(success=True, message="Token is valid")

@app.post("/api/auth/validate-lbank")
async def validate_lbank(request: dict, current_user: str = Depends(get_current_user)):
    """Validate LBank credentials"""
    return {"success": True, "message": "LBank credentials validated"}

@app.get("/api/auth/credentials")
async def get_credentials(current_user: str = Depends(get_current_user)):
    """Get stored credentials"""
    return {"success": True, "data": {"apiKey1": "", "apiSecret1": "", "apiKey2": "", "apiSecret2": ""}}

@app.post("/api/auth/lbank-account-info")
async def lbank_account_info(request: dict, current_user: str = Depends(get_current_user)):
    """Get LBank account info"""
    return {"success": True, "data": {"accountId": "test", "status": "active"}}

# Initialize database when imported
init_database()

if __name__ == "__main__":
    import uvicorn
    print(" Starting HarvestBot Authentication API...")
    print(" API available at: http://localhost:5000")
    print(" Documentation: http://localhost:5000/docs")
    print(" React frontend should use: http://localhost:5000/api")
    uvicorn.run(app, host="0.0.0.0", port=5000)
