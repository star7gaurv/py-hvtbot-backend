#!/usr/bin/env python3
"""
HarvestBot Authentication API Startup Script
Run this to start the authentication backend for your React frontend
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'jwt',
        'pydantic'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n🔧 Please install missing dependencies:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Start the HarvestBot Authentication API"""
    print("HarvestBot Authentication API Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("auth_api.py"):
        print("Error: auth_api.py not found")
        print("   Please run this script from the Harvestbot directory")
        return
    
    # Check dependencies
    print(" Checking dependencies...")
    if not check_dependencies():
        return
    
    print("All dependencies are installed")
    print("\nStarting HarvestBot Authentication API...")
    print(" Backend will be available at: http://localhost:5000")
    print(" React frontend should use: http://localhost:5000/api")
    print(" API docs will be at: http://localhost:5000/docs")
    print("\nStarting server (Press Ctrl+C to stop)...")
    print("-" * 50)
    
    try:
        # Start the FastAPI server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "auth_api:app", 
            "--host", "0.0.0.0", 
            "--port", "5000", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")

if __name__ == "__main__":
    main()
