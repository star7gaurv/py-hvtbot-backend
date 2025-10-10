#!/usr/bin/env python3
"""
Authentication API for HarvestBot - Crypto Trading Bot
Provides authentication endpoints that match the React frontend requirements
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import hashlib
# Database helper (MySQL via PyMySQL with SQLite-style placeholder wrapper)
from db import get_db_connection, init_database as init_mysql_database
import os
import uuid
import uvicorn
 
# Configuration
SECRET_KEY = "harvestbot-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# MySQL configuration is read from environment by db.py

# Initialize FastAPI app
app = FastAPI(
    title="HarvestBot Authentication API",
    description="Authentication service for HarvestBot Crypto Trading Platform",
    version="1.0.0"
)

# Add CORS middleware to allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3017",  # React frontend
        "http://localhost:3000",  # Alternative React port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models for request/response
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
    """Initialize MySQL schema (delegates to db.py)."""
    init_mysql_database()

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash

def create_access_token(data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    username = payload.get("sub")
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    
    # Verify user exists in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return username

# API Endpoints
@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return access token
    Matches React frontend expectation: POST /api/auth/login
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find user by username
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (request.username,)
        )
        user = cursor.fetchone()
        
        if not user or not verify_password(request.password, user[2]):
            conn.close()
            return AuthResponse(
                success=False,
                message="Invalid username or password"
            )
        
        # Update last login
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (datetime.utcnow(), request.username)
        )
        conn.commit()
        conn.close()
        
        # Create access token
        access_token = create_access_token(data={"sub": request.username})
        
        return AuthResponse(
            success=True,
            token=access_token,
            username=request.username,
            message="Login successful"
        )
        
    except Exception as e:
        return AuthResponse(
            success=False,
            message=f"Login failed: {str(e)}"
        )

@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """
    Register new user and return access token
    Matches React frontend expectation: POST /api/auth/signup
    """
    try:
        # Validate input
        if len(request.username) < 3:
            return AuthResponse(
                success=False,
                message="Username must be at least 3 characters long"
            )
        
        if len(request.password) < 6:
            return AuthResponse(
                success=False,
                message="Password must be at least 6 characters long"
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (request.username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return AuthResponse(
                success=False,
                message="Username already exists. Please choose a different username."
            )
        
        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(request.password)
        
        cursor.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, request.username, password_hash)
        )
        conn.commit()
        conn.close()
        
        # Create access token
        access_token = create_access_token(data={"sub": request.username})
        
        return AuthResponse(
            success=True,
            token=access_token,
            username=request.username,
            message="Account created successfully"
        )
        
    except Exception as e:
        return AuthResponse(
            success=False,
            message=f"Signup failed: {str(e)}"
        )

@app.get("/api/auth/verify", response_model=VerifyResponse)
async def verify_token_endpoint(current_user: str = Depends(get_current_user)):
    """
    Verify JWT token validity
    Matches React frontend expectation: GET /api/auth/verify
    """
    return VerifyResponse(
        success=True,
        message="Token is valid"
    )

@app.post("/api/auth/validate-lbank")
async def validate_lbank_credentials(request: dict, current_user: str = Depends(get_current_user)):
    """
    Validate LBank API credentials
    Matches React frontend expectation: POST /api/auth/validate-lbank
    """
    api_key = request.get("apiKey")
    secret_key = request.get("secretKey")
    
    if not api_key or not secret_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key and secret key are required"
        )
    
    # TODO: Implement actual LBank API validation using your existing LBank modules
    # For now, return success if keys are provided
    return {
        "success": True,
        "message": "LBank credentials are valid",
        "data": {
            "apiKey": api_key[:8] + "..." + api_key[-4:],  # Masked for security
            "isValid": True
        }
    }

@app.get("/api/auth/credentials")
async def get_lbank_credentials(current_user: str = Depends(get_current_user)):
    """
    Get user's stored LBank credentials
    Matches React frontend expectation: GET /api/auth/credentials
    """
    # TODO: Implement credential storage and retrieval
    # For now, return empty credentials
    return {
        "success": True,
        "data": {
            "apiKey1": "",
            "apiSecret1": "",
            "apiKey2": "",
            "apiSecret2": ""
        }
    }

@app.post("/api/auth/lbank-account-info")
async def get_lbank_account_info(request: dict, current_user: str = Depends(get_current_user)):
    """
    Get LBank account information
    Matches React frontend expectation: POST /api/auth/lbank-account-info
    """
    api_key = request.get("apiKey")
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key is required"
        )
    
    # TODO: Implement using your existing LBank AccountMan
    # For now, return mock data
    return {
        "success": True,
        "data": {
            "accountId": "mock_account_id",
            "status": "active",
            "balances": []
        }
    }

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "HarvestBot Authentication API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Detailed health check (MySQL)"""
    db_status = "unknown"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        db_status = "connected"
        conn.close()
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "api_version": "1.0.0"
    }

@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "HarvestBot API",
        "version": "1.0.0",
        "endpoints": [
            "POST /api/auth/login",
            "POST /api/auth/signup", 
            "GET /api/auth/verify"
        ]
    }

# Initialize database on startup
def init_db_startup():
    """Initialize database when the app starts"""
    init_database()
    print(" HarvestBot Authentication API started")
    print(" Authentication endpoints available at:")
    print("   - POST http://localhost:5001/api/auth/login")
    print("   - POST http://localhost:5001/api/auth/signup") 
    print("   - GET  http://localhost:5001/api/auth/verify")
    print(" API Documentation: http://localhost:5001/docs")

if __name__ == "__main__":
    print("Starting HarvestBot Authentication API...")
    init_db_startup()
    uvicorn.run(
        "auth_api:app",
        host="0.0.0.0",
        port=5001,
        reload=False,
        log_level="info"
    )
