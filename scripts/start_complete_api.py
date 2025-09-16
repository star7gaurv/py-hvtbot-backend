#!/usr/bin/env python
"""
Start the complete bot API server with authentication and bot management.

This script starts the FastAPI server that includes both authentication
and bot management endpoints for the crypto_gui React frontend.
"""

import uvicorn
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Add parent directory to Python path to access api module
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

def load_env_file():
    """Load environment variables from .env file if it exists"""
    env_file = parent_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        print("No .env file found, using default values")

if __name__ == "__main__":
    # Load environment variables
    load_env_file()
    
    port = int(os.getenv("API_PORT", 5001))
    host = os.getenv("API_HOST", "127.0.0.1")
    
    print(f"Starting Complete Bot API server on {host}:{port}")
    print("This includes authentication and bot management endpoints.")
    print("Available endpoints:")
    print("  - Authentication: /api/auth/login, /api/auth/signup")
    print("  - Bots: /api/bots (GET, POST)")
    print("  - Bot Details: /api/bots/{id} (GET, PUT, DELETE)")
    print("  - Bot Control: /api/bots/{id}/start, /api/bots/{id}/stop")
    print("  - Memories: /api/bots/memories (GET, POST)")
    print("  - Dashboard: /api/bots/dashboard/stats")
    print("")
    print("Press Ctrl+C to stop the server.")
    print("-" * 50)
    
    try:
        uvicorn.run(
            "api.complete_bot_api:app",
            host=host,
            port=port,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
