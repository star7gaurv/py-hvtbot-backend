#!/usr/bin/env python3
"""
Bot Runner Script for HarvestBot
This script is used to run individual bot instances with specific configurations.
Uses 'py' command for better Windows compatibility.
"""

import sys
import os
import configparser
import signal
import time
from Main import VolumeBot

def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    print(f"\nBot received signal {signum}. Shutting down gracefully...")
    sys.exit(0)

def main():
    """Main function to run the bot with configuration"""
    if len(sys.argv) != 2:
        print("Usage: python bot_runner.py <config_file_path>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    
    # Check if the file exists
    if not os.path.exists(config_file):
        # Try alternative paths if the main one doesn't exist
        bot_id = os.path.basename(config_file).replace("bot_", "").replace(".ini", "")
        
        # Try common alternative paths
        alt_paths = [
            os.path.join("configs", f"bot_{bot_id}.ini"),
            os.path.join("config/bot_configs", f"bot_{bot_id}.ini"),
            os.path.join("config", "bot_configs", f"bot_{bot_id}.ini")
        ]
        
        for alt_path in alt_paths:
            if os.path.exists(alt_path):
                config_file = alt_path
                print(f"Using alternative config path: {alt_path}")
                break
        
        # If still not found after trying alternatives
        if not os.path.exists(config_file):
            print(f"Configuration file not found: {config_file}")
            print("Tried alternative paths:")
            for path in alt_paths:
                print(f" - {path}")
            sys.exit(1)
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Read configuration
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Extract bot configuration
        bot_name = config.get('BOT', 'name', fallback='Unnamed Bot')
        bot_id = config.get('BOT', 'bot_id', fallback='unknown')
        user_id = config.get('BOT', 'user_id', fallback='unknown')
        
        # Extract API credentials
        api_key1 = config.get('DEFAULT', 'api_key', fallback='')
        secret_key1 = config.get('DEFAULT', 'secret_key', fallback='')
        api_key2 = config.get('DEFAULT', 'api_key2', fallback='')
        secret_key2 = config.get('DEFAULT', 'secret_key2', fallback='')
        
        # Extract trading parameters
        symbol = config.get('TRADING', 'symbol', fallback='hvt_usdt')
        network = config.get('TRADING', 'network', fallback='LBank')
        exchange_type = config.get('TRADING', 'exchange_type', fallback='CEX')
        min_time = config.getint('TRADING', 'min_time', fallback=60)
        max_time = config.getint('TRADING', 'max_time', fallback=300)
        min_spread = config.getfloat('TRADING', 'min_spread', fallback=0.001)
        max_spread = config.getfloat('TRADING', 'max_spread', fallback=0.005)
        buy_ratio = config.getfloat('TRADING', 'buy_ratio', fallback=0.5)
        wallet_percentage = config.getint('TRADING', 'wallet_percentage', fallback=10)
        pause_volume = config.getint('TRADING', 'pause_volume', fallback=1000000)
        
        # Validate required parameters
        if not all([api_key1, secret_key1, api_key2, secret_key2]):
            print("Missing required API credentials in configuration")
            sys.exit(1)
        
        print(f"Starting HarvestBot: {bot_name}")
        print(f"Bot ID: {bot_id}")
        print(f"User ID: {user_id}")
        print(f"Trading Pair: {symbol}")
        print(f"Network: {network}")
        print(f"Exchange Type: {exchange_type}")
        print(f"Time Range: {min_time}s - {max_time}s")
        print(f"Spread Range: {min_spread} - {max_spread}")
        print(f"Buy Ratio: {buy_ratio}")
        print(f"Wallet %: {wallet_percentage}%")
        print(f"Pause Volume: {pause_volume}")
        print("=" * 50)
        
        # Create and start the bot
        try:
            bot = VolumeBot(
                _min_time=min_time,
                _max_time=max_time,
                _wallet_percentage=wallet_percentage,
                _min_spread=min_spread,
                _max_spread=max_spread,
                _pause_volume=pause_volume,
                _buy_sell_ratio=buy_ratio,
                _apikey1=api_key1,
                _secretkey1=secret_key1,
                _apikey2=api_key2,
                _secretkey2=secret_key2,
                _trading_pair=symbol
            )
            
            print(f"Bot initialized successfully!")
            print(f"Starting trading loop...")
            
            # Start the bot's main loop
            bot.run()
            
        except KeyboardInterrupt:
            print("\nBot stopped by user (Ctrl+C)")
        except Exception as e:
            error_message = f"Bot encountered an error: {str(e)}"
            print(error_message)
            # Print more detailed error information
            import traceback
            tb = traceback.format_exc()
            print(f"Traceback:\n{tb}")
            sys.exit(1)
    
    except Exception as e:
        error_message = f"Failed to start bot: {str(e)}"
        print(error_message)
        # Print more detailed error information
        import traceback
        tb = traceback.format_exc()
        print(f"Traceback:\n{tb}")
        sys.exit(1)

if __name__ == "__main__":
    main()
