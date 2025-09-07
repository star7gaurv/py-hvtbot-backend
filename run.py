#!/usr/bin/env python3
"""
HarvestBot Main Entry Point
Simple script to start the complete system
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Main entry point for HarvestBot"""
    
    print("HarvestBot - Cryptocurrency Trading Bot")
    print("=" * 50)
    print()
    
    # Check if we're in the right directory
    current_dir = Path(__file__).parent
    os.chdir(current_dir)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "api":
            print("Starting Complete API Server...")
            print("   - Authentication & Bot Management")
            print("   - React Frontend Integration")
            print("   - Port: 5001")
            print()
            subprocess.run([VENV_PYTHON, "scripts/start_complete_api.py"])
            
        elif command == "auth":
            print("🔐 Starting Authentication API Only...")
            print("   - Basic Auth Endpoints")
            print("   - Port: 8000")
            print()
            subprocess.run([VENV_PYTHON, "scripts/start_auth_api.py"])
            
        elif command == "gui":
            print("Starting Desktop GUI...")
            print("   - Tkinter Interface")
            print("   - Local Bot Management")
            print()
            subprocess.run([VENV_PYTHON, "GUI.py"])
            
        elif command == "monitor":
            print("📊 Running System Activity Check...")
            print()
            subprocess.run([VENV_PYTHON, "monitoring/show_bot_activity.py"])
            
        elif command == "help" or command == "-h" or command == "--help":
            show_help()
            
        else:
            print(f"Unknown command: {command}")
            print("   Use 'py run.py help' for available commands")
            
    else:
        # Default action: start complete API server
        print("Starting Complete API Server (default)...")
        print("   - Authentication & Bot Management")
        print("   - React Frontend Integration")
        print("   - Port: 5001")
        print()
        print("Use 'py run.py help' for other options")
        print()
        subprocess.run([VENV_PYTHON, "scripts/start_complete_api.py"])

def show_help():
    """Show available commands"""
    print("Available commands:")
    print()
    print("  py run.py api      - Start complete API server (recommended)")
    print("  🔐 py run.py auth     - Start authentication API only")  
    print("  py run.py gui      - Start desktop GUI interface")
    print("  📊 py run.py monitor  - Check system activity")
    print("  ❓ py run.py help     - Show this help")
    print()
    print("Default behavior (no arguments):")
    print("  py run.py             # Starts complete API server")
    print()
    print("Examples:")
    print("  py run.py             # Start full system for React frontend")
    print("  py run.py gui         # Use desktop interface")
    print("  py run.py monitor     # Check if bots are running")
    print()
    print("📌 API vs Auth explanation:")
    print("  • api    = Complete system (authentication + bot management)")
    print("  • auth   = Authentication only (legacy/testing)")
    print("  • Most users should use 'api' option")

def show_menu():
    """Interactive menu for starting the system"""
    print("Default: Complete API Server started!")
    print("   This is what your React frontend needs.")
    print()
    print("Other available options:")
    print("1. Desktop GUI Interface") 
    print("2. 📊 Check System Activity")
    print("3. ❓ Show Help")
    print("4. Exit")
    print()
    print("Next time, use: py run.py <option>")
    print("   Example: py run.py gui")
    print()
    
    try:
        choice = input("Enter your choice (1-4, or press Enter to continue with API): ").strip()
        
        if choice == "" or choice == "0":
            print("\nContinuing with Complete API Server...")
            subprocess.run([VENV_PYTHON, "scripts/start_complete_api.py"])
        elif choice == "1":
            print("\nStarting Desktop GUI...")
            subprocess.run([VENV_PYTHON, "GUI.py"])
        elif choice == "2":
            print("\n📊 Checking System Activity...")
            subprocess.run([VENV_PYTHON, "monitoring/show_bot_activity.py"])
        elif choice == "3":
            show_help()
        elif choice == "4":
            print("👋 Goodbye!")
            sys.exit(0)
        else:
            print("Invalid choice. Starting API server by default...")
            subprocess.run([VENV_PYTHON, "scripts/start_complete_api.py"])
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        print("Starting API server by default...")
        subprocess.run([VENV_PYTHON, "scripts/start_complete_api.py"])

if __name__ == "__main__":
    main()
