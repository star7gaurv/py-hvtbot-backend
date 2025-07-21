import requests
import json
import sys
import time

BASE_URL = "http://localhost:5001"

def authenticate():
    """Authenticate with the API and get a token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "gaurav1",
        "password": "123456"
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"Auth response: {json.dumps(result, indent=2)}")
        return result.get("token")
    else:
        print(f"Authentication failed: {response.text}")
        sys.exit(1)

def test_bot_status(token, bot_id):
    """Test the bot status endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, get the bot details
    response = requests.get(f"{BASE_URL}/api/bots/{bot_id}", headers=headers)
    if response.status_code == 200:
        bot_data = response.json()
        print("\nBot details from database:")
        print(f"Name: {bot_data.get('name')}")
        print(f"Symbol: {bot_data.get('symbol')}")
        print(f"Status in DB: {bot_data.get('status')}")
    else:
        print(f"Failed to get bot: {response.text}")
        return
    
    # Now check the process status
    response = requests.get(f"{BASE_URL}/api/bots/{bot_id}/process_status", headers=headers)
    if response.status_code == 200:
        process_data = response.json()
        print("\nProcess status check:")
        print(json.dumps(process_data, indent=2))
        
        if process_data.get("data", {}).get("is_running"):
            print("\n✓ BOT IS ACTUALLY RUNNING")
        else:
            print("\n✗ BOT IS NOT RUNNING")
            print(f"DB Status: {process_data.get('data', {}).get('db_status')}")
            print(f"Actual Status: {process_data.get('data', {}).get('actual_status')}")
            
            # Try starting the bot
            choice = input("\nTry to start the bot? (y/n): ")
            if choice.lower() == 'y':
                print("\nAttempting to start the bot...")
                start_response = requests.post(f"{BASE_URL}/api/bots/{bot_id}/start", headers=headers)
                if start_response.status_code == 200:
                    start_data = start_response.json()
                    print(json.dumps(start_data, indent=2))
                    
                    if start_data.get("is_running"):
                        print("\n✓ BOT IS NOW RUNNING")
                    else:
                        print("\n✗ FAILED TO START BOT")
                        print(f"Error: {start_data.get('error', 'Unknown error')}")
                        print(f"Message: {start_data.get('message', 'No message')}")
                else:
                    print(f"Failed to start bot: {start_response.text}")
    else:
        print(f"Failed to check process status: {response.text}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_bot_status.py <bot_id>")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    token = authenticate()
    
    print(f"Testing status for bot: {bot_id}")
    test_bot_status(token, bot_id)
