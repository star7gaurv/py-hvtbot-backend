#!/usr/bin/env python3
"""
Complete Bot Management API for HarvestBot
Integrates with existing trading bot and provides full CRUD operations
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to access other modules
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

from fastapi import FastAPI, HTTPException, Depends, status, Query, Request, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, validator, Field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import jwt
import hashlib
# Database helper (MySQL via PyMySQL with SQLite-style placeholder wrapper) 
from db import get_db_connection, init_database as init_mysql_database
import uuid
import subprocess
import signal
import psutil
import configparser
import time

#########################
# Memory sync utilities #
#########################

def upsert_memory_for_bot(
    *,
    bot_id: str,
    user_id: str,
    name: str,
    network: str,
    symbol: str,
    exchange_type: str,
    min_time: int,
    max_time: int,
    min_spread: float,
    max_spread: float,
    buy_ratio: float,
    wallet_percentage: int,
    pause_volume: int,
    exchange_type_value: Optional[str] = None,
) -> None:
    """Create or update a memory entry mirroring the bot config (1:1 using bot_id).

    If a memory with id==bot_id exists, it's updated; otherwise it's inserted.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM bot_memories WHERE id = ? AND user_id = ?",
            (bot_id, user_id),
        )
        exists = cur.fetchone() is not None

        if exists:
            cur.execute(
                """
                UPDATE bot_memories
                SET name = ?, network = ?, symbol = ?, exchange_type = ?,
                    min_time = ?, max_time = ?, min_spread = ?, max_spread = ?,
                    buy_ratio = ?, wallet_percentage = ?, pause_volume = ?,
                    exchange_type_value = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    name,
                    network,
                    symbol,
                    exchange_type,
                    min_time,
                    max_time,
                    min_spread,
                    max_spread,
                    buy_ratio,
                    wallet_percentage,
                    pause_volume,
                    exchange_type_value,
                    bot_id,
                    user_id,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO bot_memories (
                    id, user_id, name, network, symbol, exchange_type,
                    min_time, max_time, min_spread, max_spread, buy_ratio,
                    wallet_percentage, pause_volume, exchange_type_value, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bot_id,
                    user_id,
                    name,
                    network,
                    symbol,
                    exchange_type,
                    min_time,
                    max_time,
                    min_spread,
                    max_spread,
                    buy_ratio,
                    wallet_percentage,
                    pause_volume,
                    exchange_type_value,
                    datetime.utcnow().isoformat(),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        # Non-fatal for main flows; just log
        print(f"upsert_memory_for_bot failed for bot {bot_id}: {e}")

# Configuration
SECRET_KEY = "harvestbot-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
# MySQL configuration is provided via environment variables in .env

def get_error_from_output(stdout_str: str, stderr_str: str, return_code: int) -> str:
    """Extract meaningful error messages from process output"""
    error_lines = []
    
    # Common error patterns and their user-friendly messages
    error_patterns = [
        {"pattern": "API Key permission denied", "message": "API Key permission denied - check IP restrictions and API key permissions"},
        {"pattern": "Invalid IP or permissions", "message": "API Key permission denied - check IP restrictions and API key permissions"},
        {"pattern": "currency pair nonsupport", "message": "Trading pair not supported by the exchange - check if HVT_USDT is available on LBank"},
        {"pattern": "No such file or directory: 'py'", "message": "Python executable not found - install Python or check PATH"},
        {"pattern": "Bot encountered an error", "message": None},  # Will use the actual error message
        {"pattern": "Invalid response format from API", "message": "Invalid API response - check API credentials"},
        {"pattern": "KeyError: 'data'", "message": "API response format error - the exchange returned unexpected data format"},
        {"pattern": "Error:", "message": None},  # Will use the actual error message
        {"pattern": "Failed to start bot:", "message": None}  # Will use the actual error message
    ]
    
    # Look for known error patterns first
    if stdout_str:
        for line in stdout_str.split('\n'):
            for pattern in error_patterns:
                if pattern["pattern"] in line:
                    # Use the custom message if provided, otherwise use the actual line
                    error_msg = pattern["message"] if pattern["message"] else line.strip()
                    return error_msg
    
    # Look for API errors specifically
    api_errors = []
    if stdout_str:
        for line in stdout_str.split('\n'):
            if ("Invalid response format from API" in line or "API Key" in line or 
                "error_code" in line or "permission denied" in line or 
                "currency pair nonsupport" in line):
                api_errors.append(line.strip())
    
    if api_errors:
        return '; '.join(api_errors[:2])
    
    # Look for other error messages
    if stdout_str:
        for line in stdout_str.split('\n'):
            if ('error' in line.lower() or 'failed' in line.lower() or 
                'exception' in line.lower() or 'traceback' in line.lower() or 
                'nonsupport' in line.lower() or 'denied' in line.lower() or
                'keyerror' in line.lower()):
                error_lines.append(line.strip())
    
    if stderr_str:
        for line in stderr_str.split('\n'):
            if line.strip():
                error_lines.append(line.strip())
    
    if error_lines:
        return '; '.join(error_lines[:3])  # Take first 3 error lines
    else:
        return f"Bot process exited with code {return_code}"

# Initialize FastAPI app
app = FastAPI(
    title="HarvestBot Complete API", 
    description="Authentication + Bot Management for Crypto Trading",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3017", 
        "http://localhost:3000",
        "http://127.0.0.1:3017",
        "http://127.0.0.1:3000",
        "http://localhost:5001",
        "http://127.0.0.1:5001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"{request.method} {request.url} - {response.status_code} - {process_time:.3f}s")
    return response

security = HTTPBearer()

# =================== PYDANTIC MODELS ===================

# Auth Models
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

# Bot Models
class BotBase(BaseModel):
    name: str
    symbol: str
    network: str
    exchangeType: str  # CEX or DEX
    exchangeTypeValue: Optional[str] = None
    minTime: int
    maxTime: int
    minSpread: float
    maxSpread: float
    buyRatio: float
    walletPercentage: int
    pauseVolume: int

    @validator('exchangeType')
    def validate_exchange_type(cls, v):
        if v not in ['CEX', 'DEX']:
            raise ValueError('exchangeType must be either CEX or DEX')
        return v

class BotCreate(BotBase):
    apiKey1: Optional[str] = None
    apiSecret1: Optional[str] = None
    apiKey2: Optional[str] = None
    apiSecret2: Optional[str] = None

class BotUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    network: Optional[str] = None
    exchangeType: Optional[str] = None
    exchangeTypeValue: Optional[str] = None
    minTime: Optional[int] = None
    maxTime: Optional[int] = None
    minSpread: Optional[float] = None
    maxSpread: Optional[float] = None
    buyRatio: Optional[float] = None
    walletPercentage: Optional[int] = None
    pauseVolume: Optional[int] = None
    apiKey1: Optional[str] = None
    apiSecret1: Optional[str] = None
    apiKey2: Optional[str] = None
    apiSecret2: Optional[str] = None

class BotStatusUpdate(BaseModel):
    status: str

    @validator('status')
    def validate_status(cls, v):
        if v not in ['active', 'inactive', 'paused', 'error']:
            raise ValueError('Status must be one of: active, inactive, paused, error')
        return v

class BotResponse(BaseModel):
    id: str
    name: str
    symbol: str
    network: str
    exchangeType: str
    exchangeTypeValue: Optional[str]
    minTime: int
    maxTime: int
    minSpread: float
    maxSpread: float
    buyRatio: float
    walletPercentage: int
    pauseVolume: int
    status: str
    createdAt: datetime
    updatedAt: datetime

# Memory Models
class BotMemoryCreate(BotBase):
    pass

class BotMemoryResponse(BaseModel):
    id: str
    name: str
    symbol: str
    network: str
    exchangeType: str
    exchangeTypeValue: Optional[str]
    minTime: int
    maxTime: int
    minSpread: float
    maxSpread: float
    buyRatio: float
    walletPercentage: int
    pauseVolume: int
    createdAt: datetime = Field(alias='created_at')
    
    class Config:
        populate_by_name = True  # Allow both alias and field name

# Dashboard Models
class DashboardStats(BaseModel):
    totalBots: int
    activeBots: int
    inactiveBots: int
    pausedBots: int
    errorBots: int
    totalMemories: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True

# Response wrapper models
class BotListResponse(BaseModel):
    success: bool = True
    data: List[BotResponse]

# =================== DATABASE FUNCTIONS ===================

def init_database():
    """Initialize MySQL schema via helper."""
    init_mysql_database()

# =================== AUTH FUNCTIONS ===================

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
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from token"""
    username = verify_token(credentials.credentials)
    
    # Get user from database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {"id": user[0], "username": user[1]}

# =================== BOT SERVICE FUNCTIONS ===================

def create_bot_config(bot_data: dict) -> str:
    """Create configuration file for the bot"""
    # Get the absolute path to the bot directory
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(bot_dir)
    
    # Use the new config directory structure
    config_dir = os.path.join(parent_dir, "config", "bot_configs")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, f'bot_{bot_data["id"]}.ini')
    
    # Check if there's an old config in the legacy location
    old_config_dir = os.path.join(parent_dir, "configs")
    old_config_path = os.path.join(old_config_dir, f'bot_{bot_data["id"]}.ini')
    
    # Clean up old config if it exists
    if os.path.exists(old_config_path):
        try:
            os.remove(old_config_path)
            print(f"Removed duplicate config from legacy location: {old_config_path}")
        except Exception as e:
            print(f"Failed to remove old config file: {e}")
    
    # Ensure all required fields are present - check both camelCase and snake_case
    api_key1 = bot_data.get('apiKey1', bot_data.get('api_key1', ''))
    api_secret1 = bot_data.get('apiSecret1', bot_data.get('api_secret1', ''))
    api_key2 = bot_data.get('apiKey2', bot_data.get('api_key2', ''))
    api_secret2 = bot_data.get('apiSecret2', bot_data.get('api_secret2', ''))
    
    config_content = f"""[DEFAULT]
api_key = {api_key1}
secret_key = {api_secret1}
api_key2 = {api_key2}
secret_key2 = {api_secret2}

[SIGNMETHOD]
signmethod = hmacSHA256

[TRADING]
symbol = {bot_data.get('symbol', 'mcoin_usdt')}
network = {bot_data.get('network', 'LBank')}
exchange_type = {bot_data.get('exchange_type', bot_data.get('exchangeType', 'CEX'))}
exchange_type_value = {bot_data.get('exchange_type_value', bot_data.get('exchangeTypeValue', ''))}
min_time = {bot_data.get('min_time', bot_data.get('minTime', 60))}
max_time = {bot_data.get('max_time', bot_data.get('maxTime', 300))}
min_spread = {bot_data.get('min_spread', bot_data.get('minSpread', 0.001))}
max_spread = {bot_data.get('max_spread', bot_data.get('maxSpread', 0.005))}
buy_ratio = {bot_data.get('buy_ratio', bot_data.get('buyRatio', 0.5))}
wallet_percentage = {bot_data.get('wallet_percentage', bot_data.get('walletPercentage', 10))}
pause_volume = {bot_data.get('pause_volume', bot_data.get('pauseVolume', 1000000))}

[BOT]
name = {bot_data.get('name', 'Unnamed Bot')}
bot_id = {bot_data.get('id', 'unknown')}
user_id = {bot_data.get('user_id', 'unknown')}
"""
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"Created bot config file: {config_path}")
    except Exception as e:
        print(f"Failed to create config file: {e}")
        raise
    
    return config_path

def start_bot_process(bot_data: dict) -> tuple[Optional[str], Optional[str]]:
    """Start the actual bot process using the VolumeBot trading bot
    Returns: (process_id, error_message)
    """
    try:
        print(f"Starting actual bot process for bot {bot_data.get('id', 'unknown')}")
        
        # Create configuration file for the bot
        config_path = create_bot_config(bot_data)
        
        # Get the absolute path to the bot directory
        bot_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(bot_dir)
        
        # Verify the bot runner script exists (use absolute path)
        bot_runner_path = os.path.join(parent_dir, "bot_runner.py")
        if not os.path.exists(bot_runner_path):
            error_msg = f"Bot runner script not found: {bot_runner_path}"
            print(f"{error_msg}")
            return None, error_msg
        
        # Create a log file for the bot's output (in the parent directory)
        bot_id_short = bot_data["id"].split("-")[0]
        log_dir = os.path.join(parent_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"bot_{bot_id_short}.log")
        
        with open(log_path, 'w', encoding='utf-8') as log_file:
            log_file.write(f"Starting bot: {bot_data.get('name')}\n")
            log_file.write(f"ID: {bot_data.get('id')}\n")
            log_file.write(f"Config: {config_path}\n")
            log_file.write(f"Time: {datetime.utcnow().isoformat()}\n")
            log_file.write("-" * 60 + "\n\n")
        
        # Determine the best Python executable to use
        python_executables = ['py', 'python', 'python3']
        python_cmd = None
        
        for cmd in python_executables:
            try:
                # Test if the command exists and works
                result = subprocess.run([cmd, '--version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    python_cmd = cmd
                    print(f"Using Python executable: {cmd}")
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        if not python_cmd:
            error_msg = "No suitable Python executable found (tried: py, python, python3)"
            print(error_msg)
            return None, error_msg
        
        # Start the actual bot process using the bot runner
        process = subprocess.Popen([
            python_cmd, bot_runner_path, config_path
        ], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        cwd=parent_dir,  # Set working directory to the bot project root
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )
        
        # Give the process a moment to start
        time.sleep(2)
        
        # Check if the process is still running (not crashed immediately)
        if process.poll() is None:
            print(f"Real bot process started successfully with PID: {process.pid}")
            print(f"Config file: {config_path}")
            print(f"Bot Name: {bot_data.get('name', 'Unnamed')}")
            print(f"Trading Pair: {bot_data.get('symbol', 'unknown')}")
            
            # Run a quick verification check
            try:
                # Wait a short time more to catch very early crashes
                time.sleep(3)
                if process.poll() is not None:
                    # Process already crashed
                    stdout, stderr = process.communicate(timeout=1)
                    stdout_str = stdout.decode() if stdout else ''
                    stderr_str = stderr.decode() if stderr else ''
                    
                    # Extract meaningful error from output
                    error_lines = get_error_from_output(stdout_str, stderr_str, process.returncode)
                    
                    # Log the error
                    with open(log_path, 'a', encoding='utf-8') as log_file:
                        log_file.write("BOT CRASHED SHORTLY AFTER START\n")
                        log_file.write(f"Error: {error_lines}\n\n")
                        log_file.write("STDOUT:\n")
                        log_file.write(stdout_str + "\n\n")
                        log_file.write("STDERR:\n")
                        log_file.write(stderr_str + "\n")
                    
                    print(f"Bot process crashed shortly after start")
                    print(f"Error: {error_lines}")
                    print(f"Full stdout: {stdout_str}")
                    print(f"Full stderr: {stderr_str}")
                    print(f"Log file: {log_path}")
                    
                    return None, error_lines
                
                return str(process.pid), None
            except Exception as e:
                error_msg = f"Error during verification check: {str(e)}"
                print(error_msg)
                
                # Log the error
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write(f"VERIFICATION ERROR: {error_msg}\n")
                
                return str(process.pid), None
        else:
            # Process crashed immediately - get the actual error
            try:
                stdout, stderr = process.communicate(timeout=5)
                stdout_str = stdout.decode() if stdout else ''
                stderr_str = stderr.decode() if stderr else ''
                
                # Extract meaningful error from output
                error_lines = get_error_from_output(stdout_str, stderr_str, process.returncode)
                
                # Log the error
                bot_id_short = bot_data["id"].split("-")[0]
                log_dir = "logs"
                log_path = os.path.join(log_dir, f"bot_{bot_id_short}.log")
                
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    log_file.write("BOT CRASHED IMMEDIATELY\n")
                    log_file.write(f"Error: {error_lines}\n\n")
                    log_file.write("STDOUT:\n")
                    log_file.write(stdout_str + "\n\n")
                    log_file.write("STDERR:\n")
                    log_file.write(stderr_str + "\n")
                
                print(f"Bot process crashed immediately")
                print(f"Error: {error_lines}")
                print(f"Full stdout: {stdout_str}")
                print(f"Full stderr: {stderr_str}")
                print(f"Log file: {log_path}")
                
                return None, error_lines
                
            except subprocess.TimeoutExpired:
                process.kill()
                return None, "Bot process took too long to respond and was terminated"
        
    except Exception as e:
        error_msg = f"Failed to start bot process: {str(e)}"
        print(f"{error_msg}")
        import traceback
        traceback.print_exc()
        return None, error_msg

def stop_bot_process(process_id: str) -> bool:
    """Stop the bot process gracefully"""
    try:
        if process_id:
            pid = int(process_id)
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                
                print(f"Stopping bot process {pid}...")
                
                # Try graceful termination first
                if os.name == 'nt':  # Windows
                    try:
                        # On Windows, try to send CTRL_BREAK_EVENT
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        print(f"Sent CTRL_BREAK_EVENT to process {pid}")
                    except:
                        # If that fails, try terminate
                        process.terminate()
                        print(f"Sent terminate signal to process {pid}")
                else:  # Unix/Linux
                    process.terminate()
                    print(f"Sent SIGTERM to process {pid}")
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                    print(f"Process {pid} terminated gracefully")
                    return True
                except psutil.TimeoutExpired:
                    # Force kill if graceful shutdown failed
                    print(f"Process {pid} didn't respond to termination, force killing...")
                    process.kill()
                    process.wait(timeout=5)
                    print(f"Process {pid} force killed")
                    return True
            else:
                print(f"Process {pid} not found (may have already stopped)")
                return True
    except ValueError:
        print(f"Invalid process ID: {process_id}")
        return False
    except Exception as e:
        print(f"Failed to stop bot process {process_id}: {e}")
        return False
    
    return False

def get_user_id_from_username(username: str) -> str:
    """Get user ID from username"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

def cleanup_bot_config(bot_id: str) -> bool:
    """Clean up configuration file when bot is deleted"""
    try:
        # Check both new and old config paths
        config_paths = [
            os.path.join("config/bot_configs", f'bot_{bot_id}.ini'),
            os.path.join("configs", f'bot_{bot_id}.ini')
        ]
        
        success = False
        for config_path in config_paths:
            if os.path.exists(config_path):
                os.remove(config_path)
                print(f"Cleaned up config file: {config_path}")
                success = True
        
        return True  # Return success even if no files found to clean
    except Exception as e:
        print(f"Failed to cleanup config file for bot {bot_id}: {e}")
        return False

def check_bot_process_status(bot_id: str, process_id: str) -> str:
    """Check if a bot process is still running and return updated status"""
    try:
        if not process_id:
            return "inactive"
        
        pid = int(process_id)
        if psutil.pid_exists(pid):
            process = psutil.Process(pid)
            if process.is_running():
                # Additional check: make sure it's actually our python bot process
                try:
                    cmd_line = process.cmdline()
                    if len(cmd_line) >= 3 and 'python' in cmd_line[0].lower() and 'bot_runner.py' in cmd_line[1]:
                        # It's our bot process
                        return "active"
                    else:
                        print(f"Process {pid} exists but is not a bot process: {cmd_line}")
                        return "error"
                except:
                    # If we can't check command line, assume it's running
                    return "active"
            else:
                return "error"
        else:
            return "inactive"
    except Exception as e:
        print(f"Error checking process {process_id} for bot {bot_id}: {e}")
        return "error"

def sync_bot_statuses(user_id: str) -> None:
    """Synchronize bot statuses with actual process states"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, process_id, status FROM bots 
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        
        active_bots = cursor.fetchall()
        
        for bot_id, process_id, current_status in active_bots:
            actual_status = check_bot_process_status(bot_id, process_id)
            
            if actual_status != current_status:
                print(f"Updating bot {bot_id} status from {current_status} to {actual_status}")
                cursor.execute("""
                    UPDATE bots SET status = ?, updated_at = ?
                    WHERE id = ?
                """, (actual_status, datetime.utcnow().isoformat(), bot_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error syncing bot statuses: {e}")

# =================== STARTUP EVENT ===================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()
    print("Database initialized successfully!")

# =================== API ENDPOINTS ===================

@app.get("/")
async def root():
    return {"message": "HarvestBot Complete API", "status": "running", "version": "2.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# =================== AUTH ENDPOINTS ===================

@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """User signup"""
    try:
        if len(request.username) < 3:
            return AuthResponse(success=False, message="Username must be at least 3 characters")
        
        if len(request.password) < 6:
            return AuthResponse(success=False, message="Password must be at least 6 characters")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (request.username,))
        
        if cursor.fetchone():
            conn.close()
            return AuthResponse(success=False, message="Username already exists. Please choose a different username.")
        
        user_id = str(uuid.uuid4())
        password_hash = hash_password(request.password)
        cursor.execute(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            (user_id, request.username, password_hash)
        )
        conn.commit()
        conn.close()
        
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
    """User login"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (request.username,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user or not verify_password(request.password, user[1]):
            return AuthResponse(success=False, message="Invalid username or password")
        
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
async def verify(current_user: dict = Depends(get_current_user)):
    """Token verification"""
    return VerifyResponse(success=True, message="Token is valid")

@app.post("/api/auth/validate-lbank")
async def validate_lbank(request: dict, current_user: dict = Depends(get_current_user)):
    """Validate LBank credentials"""
    return {"success": True, "message": "LBank credentials validated"}

@app.get("/api/auth/credentials")
async def get_credentials(current_user: dict = Depends(get_current_user)):
    """Get stored credentials"""
    return {"success": True, "data": {"apiKey1": "", "apiSecret1": "", "apiKey2": "", "apiSecret2": ""}}

@app.post("/api/auth/lbank-account-info")
async def lbank_account_info(request: dict, current_user: dict = Depends(get_current_user)):
    """Get LBank account info"""
    return {"success": True, "data": {"accountId": "test", "status": "active"}}

# =================== BOT ENDPOINTS ===================

@app.get("/api/bots", response_model=BotListResponse)
async def get_user_bots(current_user: dict = Depends(get_current_user)):
    """Get all bots for the authenticated user"""
    try:
        # Sync bot statuses with actual process states first
        sync_bot_statuses(current_user['id'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, symbol, network, exchange_type, exchange_type_value,
                   min_time, max_time, min_spread, max_spread, buy_ratio,
                   wallet_percentage, pause_volume, status, created_at, updated_at
            FROM bots WHERE user_id = ?
        """, (current_user['id'],))
        
        bots = cursor.fetchall()
        conn.close()
        
        bot_list = []
        for bot in bots:
            bot_list.append(BotResponse(
                id=bot[0],
                name=bot[1],
                symbol=bot[2],
                network=bot[3],
                exchangeType=bot[4],
                exchangeTypeValue=bot[5],
                minTime=bot[6],
                maxTime=bot[7],
                minSpread=bot[8],
                maxSpread=bot[9],
                buyRatio=bot[10],
                walletPercentage=bot[11],
                pauseVolume=bot[12],
                status=bot[13],
                createdAt=datetime.fromisoformat(bot[14]) if bot[14] else datetime.utcnow(),
                updatedAt=datetime.fromisoformat(bot[15]) if bot[15] else datetime.utcnow()
            ))
        
        return {"success": True, "data": bot_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bots: {str(e)}")

@app.post("/api/bots")
async def create_bot(bot_data: BotCreate, current_user: dict = Depends(get_current_user)):
    """Create a new bot"""
    try:
        bot_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bots (
                id, user_id, name, symbol, network, exchange_type, exchange_type_value,
                min_time, max_time, min_spread, max_spread, buy_ratio,
                wallet_percentage, pause_volume, api_key1, api_secret1, api_key2, api_secret2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bot_id, current_user['id'], bot_data.name, bot_data.symbol, bot_data.network,
            bot_data.exchangeType, bot_data.exchangeTypeValue, bot_data.minTime, bot_data.maxTime,
            bot_data.minSpread, bot_data.maxSpread, bot_data.buyRatio, bot_data.walletPercentage,
            bot_data.pauseVolume, bot_data.apiKey1, bot_data.apiSecret1, bot_data.apiKey2, bot_data.apiSecret2
        ))
        
        conn.commit()
        conn.close()

        # Create or update a memory snapshot for this bot (1:1 by id)
        upsert_memory_for_bot(
            bot_id=bot_id,
            user_id=current_user['id'],
            name=bot_data.name,
            network=bot_data.network,
            symbol=bot_data.symbol,
            exchange_type=bot_data.exchangeType,
            min_time=bot_data.minTime,
            max_time=bot_data.maxTime,
            min_spread=bot_data.minSpread,
            max_spread=bot_data.maxSpread,
            buy_ratio=bot_data.buyRatio,
            wallet_percentage=bot_data.walletPercentage,
            pause_volume=bot_data.pauseVolume,
            exchange_type_value=bot_data.exchangeTypeValue,
        )
        
        # Try to start the bot immediately after creation
        initial_status = "inactive"
        process_id = None
        start_message = ""
        error_message = None
        
        # Check if we have API credentials to determine if we should try to start
        has_api_credentials = bool(
            bot_data.apiKey1 and bot_data.apiSecret1 and 
            bot_data.apiKey2 and bot_data.apiSecret2
        )
        
        # For demo bots or bots with API credentials, try to start immediately
        try:
            # Create bot data dict for start_bot_process
            bot_dict = {
                'id': bot_id,
                'name': bot_data.name,
                'symbol': bot_data.symbol,
                'network': bot_data.network,
                'exchangeType': bot_data.exchangeType,
                'minTime': bot_data.minTime,
                'maxTime': bot_data.maxTime,
                'minSpread': bot_data.minSpread,
                'maxSpread': bot_data.maxSpread,
                'buyRatio': bot_data.buyRatio,
                'walletPercentage': bot_data.walletPercentage,
                'pauseVolume': bot_data.pauseVolume,
                'apiKey1': bot_data.apiKey1 or '',
                'apiSecret1': bot_data.apiSecret1 or '',
                'apiKey2': bot_data.apiKey2 or '',
                'apiSecret2': bot_data.apiSecret2 or '',
                'user_id': current_user['id']
            }
            
            print(f"Attempting to start bot {bot_id}...")
            process_id, error_message = start_bot_process(bot_dict)
            
            if process_id:
                initial_status = "active"
                start_message = f"Bot started successfully with process ID: {process_id}"
                print(start_message)
                
                # Update the database with the new status and process_id
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE bots SET status = ?, process_id = ? WHERE id = ?",
                    (initial_status, process_id, bot_id)
                )
                conn.commit()
                conn.close()
            else:
                initial_status = "error"
                start_message = f"Failed to start bot: {error_message or 'Unknown error'}"
                print(start_message)
                
                # Update the database with error status
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE bots SET status = ? WHERE id = ?",
                    (initial_status, bot_id)
                )
                conn.commit()
                conn.close()
                
        except Exception as e:
            start_message = f"Failed to auto-start bot: {e}"
            error_message = str(e)
            print(start_message)
            # If start fails, mark as error
            initial_status = "error"
            
            # Update the database with error status
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bots SET status = ? WHERE id = ?",
                (initial_status, bot_id)
            )
            conn.commit()
            conn.close()
        
        bot_response = BotResponse(
            id=bot_id,
            name=bot_data.name,
            symbol=bot_data.symbol,
            network=bot_data.network,
            exchangeType=bot_data.exchangeType,
            exchangeTypeValue=bot_data.exchangeTypeValue,
            minTime=bot_data.minTime,
            maxTime=bot_data.maxTime,
            minSpread=bot_data.minSpread,
            maxSpread=bot_data.maxSpread,
            buyRatio=bot_data.buyRatio,
            walletPercentage=bot_data.walletPercentage,
            pauseVolume=bot_data.pauseVolume,
            status=initial_status,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        response_data = {"success": True, "data": bot_response}
        
        # Add error details if bot failed to start
        if error_message:
            response_data["error"] = error_message
            response_data["message"] = start_message
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create bot: {str(e)}")

# =================== MEMORY ENDPOINTS ===================

@app.get("/api/bots/memories", response_model=List[BotMemoryResponse])
async def get_memories(current_user: dict = Depends(get_current_user)):
    """Get all saved configurations (alias for /all endpoint)"""
    return await get_all_memories(current_user)

@app.get("/api/bots/memories/all", response_model=List[BotMemoryResponse])
async def get_all_memories(current_user: dict = Depends(get_current_user)):
    """Get all saved configurations"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, network, symbol, exchange_type, min_time, max_time, 
                   min_spread, max_spread, buy_ratio, wallet_percentage, pause_volume,
                   exchange_type_value, created_at
            FROM bot_memories WHERE user_id = ?
            ORDER BY created_at DESC
        """, (current_user['id'],))
        
        memories = cursor.fetchall()
        conn.close()
        
        result = []
        for memory in memories:
            result.append(BotMemoryResponse(
                id=memory[0],
                name=memory[1],
                network=memory[2],
                symbol=memory[3],
                exchangeType=memory[4],
                minTime=memory[5],
                maxTime=memory[6],
                minSpread=memory[7],
                maxSpread=memory[8],
                buyRatio=memory[9],
                walletPercentage=memory[10],
                pauseVolume=memory[11],
                exchangeTypeValue=memory[12],
                created_at=memory[13]
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memories: {str(e)}")

@app.get("/api/bots/memories/{memory_id}", response_model=BotMemoryResponse)
async def get_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific memory by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, network, symbol, exchange_type, min_time, max_time, 
                   min_spread, max_spread, buy_ratio, wallet_percentage, pause_volume,
                   exchange_type_value, created_at
            FROM bot_memories WHERE id = ? AND user_id = ?
        """, (memory_id, current_user['id']))
        
        memory = cursor.fetchone()
        conn.close()
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return BotMemoryResponse(
            id=memory[0],
            name=memory[1],
            network=memory[2],
            symbol=memory[3],
            exchangeType=memory[4],
            minTime=memory[5],
            maxTime=memory[6],
            minSpread=memory[7],
            maxSpread=memory[8],
            buyRatio=memory[9],
            walletPercentage=memory[10],
            pauseVolume=memory[11],
            exchangeTypeValue=memory[12],
            created_at=memory[13]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")

@app.post("/api/bots/memories/{memory_id}/use", response_model=BotMemoryResponse)
async def use_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    """Use a saved memory configuration"""
    # This endpoint loads a memory - implementation depends on how you want to use it
    return await get_memory(memory_id, current_user)

@app.post("/api/bots/memories", response_model=BotMemoryResponse)
async def create_memory(memory: BotMemoryCreate, current_user: dict = Depends(get_current_user)):
    """Create a new saved configuration"""
    try:
        memory_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO bot_memories (
                id, user_id, name, network, symbol, exchange_type, min_time, max_time,
                min_spread, max_spread, buy_ratio, wallet_percentage, pause_volume,
                exchange_type_value, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id, current_user['id'], memory.name, memory.network, memory.symbol,
            memory.exchangeType, memory.minTime, memory.maxTime, memory.minSpread,
            memory.maxSpread, memory.buyRatio, memory.walletPercentage, memory.pauseVolume,
            memory.exchangeTypeValue, datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return await get_memory(memory_id, current_user)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create memory: {str(e)}")

@app.delete("/api/bots/memories/{memory_id}", response_model=MessageResponse)
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a saved memory"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM bot_memories WHERE id = ? AND user_id = ?", (memory_id, current_user['id']))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        conn.commit()
        conn.close()
        
        return MessageResponse(message="Memory deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")

# =================== DASHBOARD ENDPOINTS ===================

@app.get("/api/bots/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get bot counts by status
        cursor.execute("SELECT status, COUNT(*) FROM bots WHERE user_id = ? GROUP BY status", (current_user['id'],))
        status_counts = dict(cursor.fetchall())
        
        # Get total bots
        cursor.execute("SELECT COUNT(*) FROM bots WHERE user_id = ?", (current_user['id'],))
        total_bots = cursor.fetchone()[0]
        
        # Get total memories
        cursor.execute("SELECT COUNT(*) FROM bot_memories WHERE user_id = ?", (current_user['id'],))
        total_memories = cursor.fetchone()[0]
        
        conn.close()
        
        return DashboardStats(
            totalBots=total_bots,
            activeBots=status_counts.get('active', 0),
            inactiveBots=status_counts.get('inactive', 0),
            pausedBots=status_counts.get('paused', 0),
            errorBots=status_counts.get('error', 0),
            totalMemories=total_memories
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

# =================== BOT DETAIL ENDPOINTS ===================

@app.get("/api/bots/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific bot by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, symbol, network, exchange_type, exchange_type_value,
                   min_time, max_time, min_spread, max_spread, buy_ratio,
                   wallet_percentage, pause_volume, status, created_at, updated_at
            FROM bots WHERE id = ? AND user_id = ?
        """, (bot_id, current_user['id']))
        
        bot = cursor.fetchone()
        conn.close()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return BotResponse(
            id=bot[0],
            name=bot[1],
            symbol=bot[2],
            network=bot[3],
            exchangeType=bot[4],
            exchangeTypeValue=bot[5],
            minTime=bot[6],
            maxTime=bot[7],
            minSpread=bot[8],
            maxSpread=bot[9],
            buyRatio=bot[10],
            walletPercentage=bot[11],
            pauseVolume=bot[12],
            status=bot[13],
            createdAt=datetime.fromisoformat(bot[14]) if bot[14] else datetime.utcnow(),
            updatedAt=datetime.fromisoformat(bot[15]) if bot[15] else datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bot: {str(e)}")

@app.patch("/api/bots/{bot_id}/status")
async def update_bot_status(bot_id: str, status_data: BotStatusUpdate, current_user: dict = Depends(get_current_user)):
    """Update bot status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current bot data
        cursor.execute("""
            SELECT id, name, symbol, network, exchange_type, exchange_type_value,
                   min_time, max_time, min_spread, max_spread, buy_ratio,
                   wallet_percentage, pause_volume, status, process_id,
                   api_key1, api_secret1, api_key2, api_secret2, user_id
            FROM bots WHERE id = ? AND user_id = ?
        """, (bot_id, current_user['id']))
        
        bot = cursor.fetchone()
        if not bot:
            conn.close()
            raise HTTPException(status_code=404, detail="Bot not found")
        
        old_status = bot[13]
        process_id = bot[14]
        
        # Handle process management
        new_process_id = process_id
        error_message = None
        
        if status_data.status == "active" and old_status != "active":
            # Ensure memory snapshot is up to date before starting
            try:
                upsert_memory_for_bot(
                    bot_id=bot[0],
                    user_id=current_user['id'],
                    name=bot[1],
                    network=bot[3],
                    symbol=bot[2],
                    exchange_type=bot[4],
                    min_time=bot[6],
                    max_time=bot[7],
                    min_spread=bot[8],
                    max_spread=bot[9],
                    buy_ratio=bot[10],
                    wallet_percentage=bot[11],
                    pause_volume=bot[12],
                    exchange_type_value=bot[5],
                )
            except Exception as e:
                print(f"Failed to upsert memory before status start for bot {bot_id}: {e}")

            # Start the bot process
            bot_data = {
                'id': bot[0], 'name': bot[1], 'symbol': bot[2], 'network': bot[3],
                'exchange_type': bot[4], 'exchange_type_value': bot[5],
                'min_time': bot[6], 'max_time': bot[7], 'min_spread': bot[8],
                'max_spread': bot[9], 'buy_ratio': bot[10], 'wallet_percentage': bot[11],
                'pause_volume': bot[12], 'api_key1': bot[15], 'api_secret1': bot[16],
                'api_key2': bot[17], 'api_secret2': bot[18], 'user_id': bot[19]
            }
            new_process_id, error_message = start_bot_process(bot_data)
            
            # If failed to start, set status to error
            if not new_process_id:
                status_data.status = "error"
                
        elif status_data.status in ["inactive", "paused"] and old_status == "active":
            # Stop the bot process
            if process_id:
                stop_bot_process(process_id)
            new_process_id = None
        
        # Update bot status
        cursor.execute("""
            UPDATE bots SET status = ?, process_id = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        """, (status_data.status, new_process_id, datetime.utcnow().isoformat(), bot_id, current_user['id']))
        
        conn.commit()
        conn.close()
        
        bot_response = BotResponse(
            id=bot[0],
            name=bot[1],
            symbol=bot[2],
            network=bot[3],
            exchangeType=bot[4],
            exchangeTypeValue=bot[5],
            minTime=bot[6],
            maxTime=bot[7],
            minSpread=bot[8],
            maxSpread=bot[9],
            buyRatio=bot[10],
            walletPercentage=bot[11],
            pauseVolume=bot[12],
            status=status_data.status,
            createdAt=datetime.utcnow(),
            updatedAt=datetime.utcnow()
        )
        
        response_data = {"success": True, "data": bot_response}
        
        if status_data.status == "active":
            if new_process_id:
                # Verify bot process is actually running
                is_running = check_bot_process_status(bot_id, new_process_id) == "active"
                
                # Wait a moment and check again to catch immediate crashes
                if is_running:
                    time.sleep(5)  # Wait 5 seconds to allow any immediate crashes to happen
                    is_running = check_bot_process_status(bot_id, new_process_id) == "active"
                
                if is_running:
                    response_data["message"] = f"Bot started successfully with process ID: {new_process_id}"
                    response_data["process_status"] = "running"
                    response_data["actual_status"] = "active"
                    response_data["is_running"] = True
                else:
                    # The process started but crashed immediately
                    response_data["message"] = f"Bot started but crashed immediately"
                    response_data["process_status"] = "crashed"
                    response_data["actual_status"] = "error"
                    response_data["is_running"] = False
                    response_data["error"] = error_message or "Unknown error - bot process terminated"
                    # Update the database to reflect actual status
                    conn = get_db_connection()
                    conn.execute("UPDATE bots SET status = ? WHERE id = ?", ("error", bot_id))
                    conn.commit()
                    conn.close()
                    bot_response.status = "error"  # Update the response object as well
            else:
                response_data["message"] = f"Bot failed to start: {error_message or 'Unknown error'}"
                response_data["process_status"] = "failed"
                response_data["actual_status"] = "error"
                response_data["is_running"] = False
                response_data["error"] = error_message
        elif status_data.status == "error" and error_message:
            response_data["error"] = error_message
            response_data["message"] = f"Bot failed to start: {error_message}"
            response_data["process_status"] = "failed"
            response_data["actual_status"] = "error"
            response_data["is_running"] = False
        else:
            response_data["message"] = f"Bot status updated to {status_data.status} successfully"
            response_data["process_status"] = "inactive"
            response_data["actual_status"] = status_data.status
            response_data["is_running"] = False
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bot status: {str(e)}")

@app.put("/api/bots/{bot_id}", response_model=BotResponse)
async def update_bot(bot_id: str, bot_data: BotUpdate, current_user: dict = Depends(get_current_user)):
    """Update bot configuration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        update_data = bot_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key == 'exchangeType':
                update_fields.append('exchange_type = ?')
                update_values.append(value)
            elif key == 'exchangeTypeValue':
                update_fields.append('exchange_type_value = ?')
                update_values.append(value)
            elif key == 'minTime':
                update_fields.append('min_time = ?')
                update_values.append(value)
            elif key == 'maxTime':
                update_fields.append('max_time = ?')
                update_values.append(value)
            elif key == 'minSpread':
                update_fields.append('min_spread = ?')
                update_values.append(value)
            elif key == 'maxSpread':
                update_fields.append('max_spread = ?')
                update_values.append(value)
            elif key == 'buyRatio':
                update_fields.append('buy_ratio = ?')
                update_values.append(value)
            elif key == 'walletPercentage':
                update_fields.append('wallet_percentage = ?')
                update_values.append(value)
            elif key == 'pauseVolume':
                update_fields.append('pause_volume = ?')
                update_values.append(value)
            elif key == 'apiKey1':
                update_fields.append('api_key1 = ?')
                update_values.append(value)
            elif key == 'apiSecret1':
                update_fields.append('api_secret1 = ?')
                update_values.append(value)
            elif key == 'apiKey2':
                update_fields.append('api_key2 = ?')
                update_values.append(value)
            elif key == 'apiSecret2':
                update_fields.append('api_secret2 = ?')
                update_values.append(value)
            else:
                update_fields.append(f'{key} = ?')
                update_values.append(value)
        
        if update_fields:
            update_fields.append('updated_at = ?')
            update_values.append(datetime.utcnow().isoformat())
            update_values.extend([bot_id, current_user['id']])
            
            query = f"UPDATE bots SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
            cursor.execute(query, update_values)
            
            if cursor.rowcount == 0:
                conn.close()
                raise HTTPException(status_code=404, detail="Bot not found")
        
        # Get updated bot
        cursor.execute("""
            SELECT id, name, symbol, network, exchange_type, exchange_type_value,
                   min_time, max_time, min_spread, max_spread, buy_ratio,
                   wallet_percentage, pause_volume, status, created_at, updated_at
            FROM bots WHERE id = ? AND user_id = ?
        """, (bot_id, current_user['id']))
        
        bot = cursor.fetchone()
        conn.commit()
        conn.close()
        
        response_obj = BotResponse(
            id=bot[0],
            name=bot[1],
            symbol=bot[2],
            network=bot[3],
            exchangeType=bot[4],
            exchangeTypeValue=bot[5],
            minTime=bot[6],
            maxTime=bot[7],
            minSpread=bot[8],
            maxSpread=bot[9],
            buyRatio=bot[10],
            walletPercentage=bot[11],
            pauseVolume=bot[12],
            status=bot[13],
            createdAt=datetime.fromisoformat(bot[14]) if bot[14] else datetime.utcnow(),
            updatedAt=datetime.fromisoformat(bot[15]) if bot[15] else datetime.utcnow()
        )

        # Upsert memory snapshot to reflect latest configuration
        try:
            upsert_memory_for_bot(
                bot_id=bot[0],
                user_id=current_user['id'],
                name=bot[1],
                network=bot[3],
                symbol=bot[2],
                exchange_type=bot[4],
                min_time=bot[6],
                max_time=bot[7],
                min_spread=bot[8],
                max_spread=bot[9],
                buy_ratio=bot[10],
                wallet_percentage=bot[11],
                pause_volume=bot[12],
                exchange_type_value=bot[5],
            )
        except Exception as e:
            print(f"Failed to upsert memory during update for bot {bot_id}: {e}")

        return response_obj
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bot: {str(e)}")

@app.delete("/api/bots/{bot_id}", response_model=MessageResponse)
async def delete_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a bot"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get bot with process info
        cursor.execute("""
            SELECT process_id, status FROM bots WHERE id = ? AND user_id = ?
        """, (bot_id, current_user['id']))
        
        bot = cursor.fetchone()
        if not bot:
            conn.close()
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Stop process if running
        if bot[0] and bot[1] == "active":
            stop_bot_process(bot[0])
        
        # Clean up configuration file
        cleanup_bot_config(bot_id)
        
        # Delete bot
        cursor.execute("DELETE FROM bots WHERE id = ? AND user_id = ?", (bot_id, current_user['id']))
        conn.commit()
        conn.close()
        
        # Cleanup config file
        cleanup_bot_config(bot_id)
        
        return MessageResponse(message="Bot deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete bot: {str(e)}")

@app.post("/api/bots/{bot_id}/start")
async def start_bot(bot_id: str, current_user: dict = Depends(get_current_user)):
    """Start a bot and verify it's actually running"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current bot data
        cursor.execute("""
            SELECT id, name, symbol, network, exchange_type, exchange_type_value,
                   min_time, max_time, min_spread, max_spread, buy_ratio,
                   wallet_percentage, pause_volume, status, process_id,
                   api_key1, api_secret1, api_key2, api_secret2, user_id
            FROM bots WHERE id = ? AND user_id = ?
        """, (bot_id, current_user['id']))
        
        bot = cursor.fetchone()
        if not bot:
            conn.close()
            raise HTTPException(status_code=404, detail="Bot not found")
        
        old_status = bot[13]
        process_id = bot[14]
        
        # First, check if the bot is already running
        if process_id and check_bot_process_status(bot_id, process_id) == "active":
            conn.close()
            return {
                "success": True,
                "data": {
                    "id": bot[0],
                    "name": bot[1],
                    "symbol": bot[2],
                    "status": "active",
                    "process_id": process_id
                },
                "message": "Bot is already running",
                "process_status": "running",
                "actual_status": "active",
                "is_running": True
            }
        
        # If bot was previously marked as active but process is not running,
        # or if we're explicitly starting the bot
        bot_data = {
            'id': bot[0], 'name': bot[1], 'symbol': bot[2], 'network': bot[3],
            'exchange_type': bot[4], 'exchange_type_value': bot[5],
            'min_time': bot[6], 'max_time': bot[7], 'min_spread': bot[8],
            'max_spread': bot[9], 'buy_ratio': bot[10], 'wallet_percentage': bot[11],
            'pause_volume': bot[12], 'api_key1': bot[15], 'api_secret1': bot[16],
            'api_key2': bot[17], 'api_secret2': bot[18], 'user_id': bot[19]
        }
        
        # Clean up any old configs in wrong location
        cleanup_bot_config(bot_id)
        
        # Ensure a memory snapshot exists/updated before starting
        try:
            upsert_memory_for_bot(
                bot_id=bot[0],
                user_id=current_user['id'],
                name=bot[1],
                network=bot[3],
                symbol=bot[2],
                exchange_type=bot[4],
                min_time=bot[6],
                max_time=bot[7],
                min_spread=bot[8],
                max_spread=bot[9],
                buy_ratio=bot[10],
                wallet_percentage=bot[11],
                pause_volume=bot[12],
                exchange_type_value=bot[5],
            )
        except Exception as e:
            print(f"Failed to upsert memory before starting bot {bot_id}: {e}")

        # Start the bot process
        new_process_id, error_message = start_bot_process(bot_data)
        
        response = {
            "success": True if new_process_id else False,
            "data": {
                "id": bot[0],
                "name": bot[1],
                "symbol": bot[2]
            }
        }
        
        if new_process_id:
            # Wait a moment to allow for immediate crashes
            time.sleep(5)
            
            # Check if it's actually running
            is_running = check_bot_process_status(bot_id, new_process_id) == "active"
            
            if is_running:
                # Update status in DB
                cursor.execute(
                    "UPDATE bots SET status = ?, process_id = ?, updated_at = ? WHERE id = ?",
                    ("active", new_process_id, datetime.utcnow().isoformat(), bot_id)
                )
                conn.commit()
                
                response["message"] = f"Bot started successfully with process ID: {new_process_id}"
                response["process_id"] = new_process_id
                response["process_status"] = "running"
                response["actual_status"] = "active"
                response["is_running"] = True
            else:
                # Bot crashed immediately
                cursor.execute(
                    "UPDATE bots SET status = ?, updated_at = ? WHERE id = ?",
                    ("error", datetime.utcnow().isoformat(), bot_id)
                )
                conn.commit()
                
                response["success"] = False
                response["message"] = "Bot started but crashed immediately"
                response["error"] = error_message or "Unknown error - bot process terminated"
                response["process_status"] = "crashed"
                response["actual_status"] = "error"
                response["is_running"] = False
        else:
            # Failed to start
            cursor.execute(
                "UPDATE bots SET status = ?, updated_at = ? WHERE id = ?",
                ("error", datetime.utcnow().isoformat(), bot_id)
            )
            conn.commit()
            
            response["success"] = False
            response["message"] = f"Failed to start bot: {error_message or 'Unknown error'}"
            response["error"] = error_message
            response["process_status"] = "failed"
            response["actual_status"] = "error"
            response["is_running"] = False
        
        conn.close()
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")

@app.get("/api/bots/{bot_id}/process_status")
async def get_bot_process_status(bot_id: str, current_user: dict = Depends(get_current_user)):
    """Get the actual running status of a bot process"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, status, process_id
            FROM bots WHERE id = ? AND user_id = ?
        """, (bot_id, current_user['id']))
        
        bot = cursor.fetchone()
        conn.close()
        
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        db_status = bot[2]
        process_id = bot[3]
        
        # Get the actual process status
        actual_status = check_bot_process_status(bot_id, process_id)
        
        # If DB says active but process is not running, update DB
        if db_status == "active" and actual_status != "active":
            conn = get_db_connection()
            conn.execute(
                "UPDATE bots SET status = ?, updated_at = ? WHERE id = ?",
                ("error", datetime.utcnow().isoformat(), bot_id)
            )
            conn.commit()
            conn.close()
            db_status = "error"
        
        return {
            "success": True,
            "data": {
                "id": bot[0],
                "name": bot[1],
                "db_status": db_status,
                "actual_status": actual_status,
                "process_id": process_id,
                "is_running": actual_status == "active"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bot process status: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5001)
