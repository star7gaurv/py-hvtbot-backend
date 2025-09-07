#!/usr/bin/env python3
"""
API Configuration Validator and Helper
Provides guidance on fixing API-related issues
"""

import sys
import os
import configparser
from pathlib import Path

def validate_config_file(config_file):
    """Validate and provide guidance on fixing configuration issues"""
    
    print("🔍 LBank Trading Bot Configuration Validator")
    print("=" * 60)
    
    # Read configuration
    if not os.path.exists(config_file):
        print(f"❌ Configuration file not found: {config_file}")
        return
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # Extract configuration
    api_key1 = config.get('DEFAULT', 'api_key', fallback='')
    secret_key1 = config.get('DEFAULT', 'secret_key', fallback='')
    api_key2 = config.get('DEFAULT', 'api_key2', fallback='')
    secret_key2 = config.get('DEFAULT', 'secret_key2', fallback='')
    symbol = config.get('TRADING', 'symbol', fallback='')
    network = config.get('TRADING', 'network', fallback='')
    
    print(f"📊 Configuration Summary:")
    print(f"   Trading Pair: {symbol}")
    print(f"   Network: {network}")
    print(f"   API Key 1: {api_key1[:8]}...{api_key1[-8:] if len(api_key1) > 16 else api_key1}")
    print(f"   API Key 2: {api_key2[:8]}...{api_key2[-8:] if len(api_key2) > 16 else api_key2}")
    print()
    
    # Provide solutions
    print("🔧 Common Issues and Solutions:")
    print("-" * 40)
    
    print("1. ❌ API Key Permission Denied (Error 10022)")
    print("   🏠 IP Restriction Issue:")
    print("      • Your IP address is not whitelisted in LBank API settings")
    print("      • Go to LBank → API Management → Edit API → IP Restrictions")
    print("      • Add your current IP address or use 0.0.0.0/0 for any IP")
    print("      • Note: Using 0.0.0.0/0 is less secure but works for testing")
    print()
    
    print("   🔑 API Permission Issue:")
    print("      • Your API key doesn't have trading permissions")
    print("      • Go to LBank → API Management → Edit API → Permissions")
    print("      • Enable 'Trade' permission (required for trading bots)")
    print("      • Enable 'Read' permission (required for balance checking)")
    print()
    
    print("2. ❌ Currency Pair Not Supported")
    print(f"   🔄 Trading Pair '{symbol}' Issue:")
    print("      • HVT_USDT might not be available on LBank")
    print("      • Check LBank exchange for available trading pairs")
    print("      • Common working pairs: lbt_usdt, btc_usdt, eth_usdt")
    print("      • Update the 'symbol' value in your config file")
    print()
    
    print("3. ✅ Recommended Test Configuration:")
    print("   📝 Create a test config with:")
    print("      • Working trading pair: lbt_usdt")
    print("      • Lower wallet percentage: 1%")
    print("      • Longer wait times: 60-300 seconds")
    print("      • Valid API keys with proper permissions")
    print()
    
    print("4. 🧪 Testing Steps:")
    print("   1️⃣ Fix IP restrictions in LBank")
    print("   2️⃣ Enable trading permissions for API keys")
    print("   3️⃣ Test with a supported trading pair (lbt_usdt)")
    print("   4️⃣ Use small amounts for testing (1% wallet)")
    print("   5️⃣ Monitor logs for any remaining issues")
    print()
    
    # Generate a test configuration
    print("📋 Sample Test Configuration:")
    print("-" * 40)
    
    test_config = f"""[DEFAULT]
api_key = YOUR_API_KEY_1
secret_key = YOUR_SECRET_KEY_1
api_key2 = YOUR_API_KEY_2
secret_key2 = YOUR_SECRET_KEY_2

[SIGNMETHOD]
signmethod = hmacSHA256

[TRADING]
symbol = lbt_usdt
network = LBank
exchange_type = CEX
exchange_type_value = MM to MM
min_time = 60
max_time = 300
min_spread = 0.001
max_spread = 0.005
buy_ratio = 0.5
wallet_percentage = 1
pause_volume = 1000000

[BOT]
name = test_bot
bot_id = {config.get('BOT', 'bot_id') if config.has_option('BOT', 'bot_id') else 'your-bot-id'}
user_id = {config.get('BOT', 'user_id') if config.has_option('BOT', 'user_id') else 'your-user-id'}
"""
    
    print(test_config)
    
    print("=" * 60)
    print("💡 Next Steps:")
    print("1. Fix LBank API settings (IP + Permissions)")
    print("2. Update config with supported trading pair")
    print("3. Test with small amounts first")
    print("4. Check bot logs for detailed error information")
    print()
    print("📞 Need Help?")
    print("• Check LBank API documentation")
    print("• Verify trading pair availability on LBank website")
    print("• Test API credentials with LBank's official tools first")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python api_config_helper.py <config_file_path>")
        print("Example: python api_config_helper.py config/bot_configs/bot_6332e594-b2c9-4a7a-a28c-7ca2aa6ecb05.ini")
        sys.exit(1)
    
    config_file = sys.argv[1]
    validate_config_file(config_file)
