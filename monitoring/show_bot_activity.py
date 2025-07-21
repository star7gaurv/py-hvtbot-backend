#!/usr/bin/env python3
"""
Bot Activity Monitor
Simple script to check bot activity and status

Usage:
    py show_bot_activity.py              # Show general activity overview
    py show_bot_activity.py <pid>        # Show details for specific process ID

Examples:
    py show_bot_activity.py              # General status check
    py show_bot_activity.py 1234         # Check specific bot process with PID 1234
"""

import psutil
import os
import sqlite3
from datetime import datetime

def check_bot_activity():
    """Check bot activity across all components"""
    print("HarvestBot Activity Monitor")
    print("=" * 50)
    
    # Check for running Python processes
    print("\n1. Active Bot Processes:")
    bot_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' or proc.info['name'] == 'py.exe':
                cmdline = ' '.join(proc.info['cmdline'])
                if 'bot_runner.py' in cmdline or 'Main.py' in cmdline:
                    runtime = (datetime.now() - datetime.fromtimestamp(proc.create_time())).total_seconds()
                    print(f"   Process ID: {proc.info['pid']}")
                    print(f"   Runtime: {runtime:.1f} seconds ({runtime/60:.1f} minutes)")
                    print(f"   Command: {cmdline}")
                    print(f"   Memory: {proc.memory_info().rss / 1024 / 1024:.2f} MB")
                    bot_processes.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not bot_processes:
        print("   No active bot processes found")
    
    # Check configuration files
    print("\n2. Bot Configurations:")
    config_dir = "config/bot_configs"
    if os.path.exists(config_dir):
        configs = [f for f in os.listdir(config_dir) if f.endswith('.ini')]
        print(f"   Found {len(configs)} bot configuration files")
        for config in configs:
            config_path = os.path.join(config_dir, config)
            stat = os.stat(config_path)
            creation_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   {config} - Modified: {creation_time}")
    else:
        print("   No bot configuration directory found")
    
    # Check database
    print("\n3. Database Status:")
    db_path = "data/harvestbot_users.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bots")
            bot_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM bots WHERE status = 'active'")
            active_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM bots WHERE status = 'error'")
            error_count = cursor.fetchone()[0]
            print(f"   Total bots in database: {bot_count}")
            print(f"   Active bots: {active_count}")
            print(f"   Error bots: {error_count}")
            
            # Show recent bot activity
            cursor.execute("SELECT name, status, updated_at FROM bots ORDER BY updated_at DESC LIMIT 5")
            recent_bots = cursor.fetchall()
            if recent_bots:
                print("   Recent bot activity:")
                for name, status, updated_at in recent_bots:
                    print(f"     {name}: {status} (Updated: {updated_at})")
            
            conn.close()
        except Exception as e:
            print(f"   Database check failed: {e}")
    else:
        print("   Database file not found")
    
    # Check recent trading activity
    print("\n4. Recent Trading Activity:")
    data_files = ["data/lbank_accuracy_data.txt", "data/keys.txt"]
    for data_file in data_files:
        if os.path.exists(data_file):
            stat = os.stat(data_file)
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   {os.path.basename(data_file)} last modified: {mod_time}")
            
            # Check if recently modified (within last hour)
            time_diff = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
            if time_diff.total_seconds() < 3600:
                print(f"     Recent activity detected (within last hour)")
            else:
                print(f"     No recent activity ({time_diff.total_seconds()/3600:.1f} hours ago)")
        else:
            print(f"   {data_file} not found")
    
    # Check API server status
    print("\n5. API Server Status:")
    api_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' or proc.info['name'] == 'py.exe':
                cmdline = ' '.join(proc.info['cmdline'])
                if 'complete_bot_api.py' in cmdline or 'uvicorn' in cmdline:
                    print(f"   API Server running (PID: {proc.info['pid']})")
                    print(f"   Command: {cmdline}")
                    api_processes.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not api_processes:
        print("   No API server processes found")
    
    print("\n" + "=" * 50)
    if bot_processes:
        print("STATUS: BOT PROCESSES ARE ACTIVELY RUNNING")
        print(f"Active bot processes: {len(bot_processes)}")
    else:
        print("STATUS: NO ACTIVE BOTS DETECTED")
    
    if api_processes:
        print("STATUS: API SERVER IS RUNNING")
    else:
        print("STATUS: API SERVER NOT DETECTED")

def show_process_details(pid):
    """Show detailed information about a specific process"""
    try:
        proc = psutil.Process(pid)
        print(f"\nDetailed Process Information (PID: {pid}):")
        print(f"Name: {proc.name()}")
        print(f"Status: {proc.status()}")
        print(f"CPU Usage: {proc.cpu_percent()}%")
        print(f"Memory Usage: {proc.memory_info().rss / 1024 / 1024:.2f} MB")
        print(f"Create Time: {datetime.fromtimestamp(proc.create_time())}")
        print(f"Command Line: {' '.join(proc.cmdline())}")
        
        # Check if it's still running
        if proc.is_running():
            print("Process is currently running")
        else:
            print("Process is not running")
            
    except psutil.NoSuchProcess:
        print(f"Process with PID {pid} not found")
    except Exception as e:
        print(f"Error checking process {pid}: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        try:
            pid = int(sys.argv[1])
            show_process_details(pid)
        except ValueError:
            print("Invalid PID provided. Showing general activity instead.")
            check_bot_activity()
    else:
        check_bot_activity()
