#!/usr/bin/env python3
"""
Bot Monitor Script - Check if the bot is actively running and showing its activity
"""

import psutil
import time
import sys

def monitor_bot_process(pid):
    """Monitor a specific bot process"""
    try:
        process = psutil.Process(pid)
        
        print(f"=== Bot Process Monitor (PID: {pid}) ===")
        print(f"Process Name: {process.name()}")
        print(f"Command Line: {' '.join(process.cmdline())}")
        print(f"Status: {process.status()}")
        print(f"CPU Percent: {process.cpu_percent()}%")
        print(f"Memory Usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
        print(f"Create Time: {time.ctime(process.create_time())}")
        print(f"Running Time: {time.time() - process.create_time():.1f} seconds")
        
        # Check if process is actually running (not zombie)
        if process.is_running():
            print("Bot process is ACTIVELY RUNNING")
            
            # Monitor for a few seconds to see if there's any activity
            print("\nMonitoring activity for 10 seconds...")
            initial_cpu = process.cpu_percent()
            time.sleep(1)
            
            for i in range(10):
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                print(f"[{i+1:2d}s] CPU: {cpu_percent:5.1f}% | Memory: {memory_mb:6.1f}MB | Status: {process.status()}")
                time.sleep(1)
                
                if not process.is_running():
                    print("Process stopped during monitoring!")
                    return False
            
            print("Bot has been running consistently for the monitoring period")
            return True
        else:
            print("Process is not running")
            return False
            
    except psutil.NoSuchProcess:
        print(f"No process found with PID {pid}")
        return False
    except Exception as e:
        print(f"Error monitoring process: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python monitor_bot.py <pid>")
        sys.exit(1)
    
    try:
        pid = int(sys.argv[1])
        monitor_bot_process(pid)
    except ValueError:
        print("Error: PID must be a number")
        sys.exit(1)
