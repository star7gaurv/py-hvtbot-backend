# 🤖 Crypto Volume Trading Bot - How It Works

## 📋 Overview

The **py-hvtbot-backend** is an automated cryptocurrency trading bot designed to generate trading volume on the LBank exchange. It operates by coordinating trades between two separate accounts to create market activity.

---

## 🎯 What Does This Bot Do?

The bot automatically executes cryptocurrency trades between two accounts to:

- **Generate Trading Volume**: Creates consistent market activity
- **Maintain Market Presence**: Keeps the trading pair active with regular transactions
- **Simulate Natural Trading**: Uses randomization to mimic human trading patterns
- **Balance Management**: Automatically manages funds between accounts

---

## 🔄 The Two-Account System

### Why Two Accounts?

The bot requires **two separate LBank exchange accounts** to function:

- **Account 1**: Acts as the seller in some trades, buyer in others
- **Account 2**: Acts as the buyer in some trades, seller in others

Both accounts need:
- ✅ API keys configured
- ✅ Sufficient balance (both USDT and the trading token)
- ✅ Trading permissions enabled

### How They Work Together

The accounts work in a **ping-pong pattern**:

```
Round 1: Account 1 Sells → Account 2 Buys
Round 2: Account 2 Sells → Account 1 Buys
Round 3: Account 1 Sells → Account 2 Buys
... and so on
```

This creates a back-and-forth trading flow that generates volume.

---

## 💡 Trading Strategy Explained

### 1. **Price Selection**

The bot doesn't just pick random prices. It works intelligently:

- **Reads the Order Book**: Gets current bid (buy) and ask (sell) prices
- **Calculates Mid-Price**: Finds a price between bid and ask
- **Adds Randomization**: Slightly varies the price to look natural
- **Respects Spread Limits**: Only trades when spread is within your configured range

**Example:**
```
Current Bid: $0.0100
Current Ask: $0.0105
Bot Selects: $0.01023 (random between bid and ask)
```

### 2. **Order Splitting**

To appear more human-like, the bot splits large orders into smaller chunks:

**Instead of:**
```
One order: 10,000 HVT at $0.0102
```

**It does:**
```
Order 1: 2,500 HVT at $0.01020
Wait 30 seconds...
Order 2: 4,000 HVT at $0.01024
Wait 45 seconds...
Order 3: 3,500 HVT at $0.01019
```

This makes the trading activity look organic and natural.

### 3. **Timing Randomization**

The bot doesn't trade at fixed intervals. Instead:

- You set a **minimum** and **maximum** wait time (e.g., 30-300 seconds)
- The bot randomly picks a time in that range
- Each trade happens at unpredictable intervals
- This mimics real human trading behavior

---

## 🎛️ Configurable Parameters

You have full control over how the bot operates:

### **Time Settings**
- **Min Time**: Shortest wait between trades (e.g., 30 seconds)
- **Max Time**: Longest wait between trades (e.g., 5 minutes)

### **Volume Settings**
- **Wallet Percentage**: How much of your balance to use per trade (e.g., 5%)
- **Pause Volume**: Stop trading if daily volume exceeds this limit (safety feature)

### **Price Settings**
- **Min Spread**: Minimum acceptable spread to trade (e.g., 0.01%)
- **Max Spread**: Maximum acceptable spread to trade (e.g., 10%)

### **Trading Behavior**
- **Buy/Sell Ratio**: Controls whether orders appear more as "buys" or "sells" in the order book
- **Trading Pair**: Which cryptocurrency to trade (e.g., HVT/USDT)

---

## 🔍 Step-by-Step: A Single Trading Cycle

Let's walk through exactly what happens when the bot executes one trade cycle:

### **Step 1: Check Daily Volume**
```
✓ Check: Has today's volume reached the pause limit?
  → If YES: Skip trading and wait
  → If NO: Continue to Step 2
```

### **Step 2: Get Market Data**
```
✓ Fetch current order book
✓ Get bid price: $0.0100
✓ Get ask price: $0.0105
✓ Calculate spread: 5%
```

### **Step 3: Verify Spread is Acceptable**
```
✓ Check: Is 5% spread within min (0.01%) and max (10%)?
  → If YES: Continue
  → If NO: Use backup strategy or wait
```

### **Step 4: Check Account Balances**
```
Account 1:
  - USDT: $1,000
  - HVT: 50,000 tokens

Account 2:
  - USDT: $1,200
  - HVT: 45,000 tokens

✓ Both accounts have sufficient balance
```

### **Step 5: Calculate Trade Amount**
```
✓ Wallet percentage: 5%
✓ Account 1 has 50,000 HVT
✓ Trade amount: 50,000 × 5% = 2,500 HVT
```

### **Step 6: Split the Order**
```
✓ Randomly split 2,500 HVT into chunks:
  - 800 HVT
  - 1,100 HVT
  - 600 HVT
```

### **Step 7: Execute Trades**
```
Trade 1:
  Account 1: SELL 800 HVT at $0.01023
  Account 2: BUY 800 HVT at $0.01023
  Wait 47 seconds...

Trade 2:
  Account 1: SELL 1,100 HVT at $0.01019
  Account 2: BUY 1,100 HVT at $0.01019
  Wait 62 seconds...

Trade 3:
  Account 1: SELL 600 HVT at $0.01021
  Account 2: BUY 600 HVT at $0.01021
```

### **Step 8: Wait and Repeat**
```
✓ Wait random time (between min and max)
✓ Next cycle starts with Account 2 selling to Account 1
```

---

## 🛡️ Safety Features

The bot includes several protective mechanisms:

### **1. Volume Pause**
```
If daily volume > pause limit:
  → Stop all trading
  → Resume next day
```
**Why?** Prevents excessive volume that might look suspicious.

### **2. Balance Verification**
```
Before each trade:
  → Check if accounts have enough USDT
  → Check if accounts have enough tokens
  → If insufficient: Skip trade and alert
```
**Why?** Prevents failed orders and errors.

### **3. Spread Monitoring**
```
If spread is too wide or too narrow:
  → Use backup trading strategy
  → Or wait for better conditions
```
**Why?** Ensures trades happen at reasonable prices.

### **4. Order Book Analysis**
```
Continuously monitors:
  → Current bid/ask prices
  → Market depth
  → Recent price movements
```
**Why?** Makes intelligent trading decisions.

---

## 🎨 Special Trading Strategies

### **Strategy 1: Normal Spread Trading**
When there's a good spread between bid and ask:
- Place orders at various mid-prices
- Create natural-looking volume
- Alternate between accounts

### **Strategy 2: No-Gap Trading**
When bid and ask prices are too close:
- Use minimum transaction amounts
- Trade at existing prices (market taking)
- Create new price levels slightly outside current range

### **Strategy 3: Order Appearance Control**
Based on your buy/sell ratio setting:
- Some trades appear as "buy orders" in the market
- Some trades appear as "sell orders" in the market
- This creates realistic market depth on both sides

---

## 📊 What Happens to Your Funds?

### **The Net Effect**

After a complete trading cycle (forward + backward):

**Account 1:**
```
Before: 1,000 USDT + 50,000 HVT
After:  ~1,000 USDT + ~50,000 HVT (roughly the same)
```

**Account 2:**
```
Before: 1,200 USDT + 45,000 HVT
After:  ~1,200 USDT + ~45,000 HVT (roughly the same)
```

**Key Points:**
- ✅ Tokens move back and forth between accounts
- ✅ Overall balances remain relatively stable
- ⚠️ Small losses occur due to exchange fees
- ⚠️ Requires initial balance in both accounts

---

## 🎯 Use Cases

This bot is typically used for:

1. **New Token Launches**: Generate initial trading activity
2. **Market Making**: Maintain active trading presence
3. **Liquidity Provision**: Keep the order book active
4. **Volume Metrics**: Demonstrate market interest

---

## ⚙️ How to Control the Bot

### **Through the GUI (Graphical Interface)**
- Start/stop the bot
- Monitor real-time trading activity
- View account balances
- Check trading statistics

### **Through Configuration Files**
- Set trading parameters
- Configure API keys
- Adjust trading behavior
- Set safety limits

### **Through the API**
- Programmatic control
- Integration with other systems
- Remote monitoring
- Automated management

---

## 📈 What You'll See

### **On the Exchange:**
```
Recent Trades:
12:34:56 - BUY 800 HVT at $0.01023
12:35:43 - SELL 1,100 HVT at $0.01019
12:36:45 - BUY 600 HVT at $0.01021
12:38:12 - SELL 950 HVT at $0.01020
```

### **24h Volume:**
```
Before bot: $1,200
After 6 hours: $8,500
After 12 hours: $17,300
After 24 hours: $35,000+
```

### **Order Book Activity:**
```
Continuous buy and sell orders at various price levels
Active market depth on both sides
Regular price updates
```

---

## 🔔 Important Considerations

### **Financial Requirements**
- Both accounts need adequate starting balance
- Consider exchange trading fees (typically 0.1-0.2% per trade)
- Budget for potential small losses from fees

### **Market Conditions**
- Works best with stable price ranges
- May pause during extreme volatility
- Adapts to changing spread conditions

### **Monitoring**
- Check bot status regularly
- Review account balances
- Monitor for any errors or issues
- Keep API keys secure

### **Legal & Ethical**
- ⚠️ Wash trading is illegal in many jurisdictions
- ⚠️ May violate exchange terms of service
- ⚠️ Could result in account suspension
- ⚠️ Consult legal advice before use

---

## 🚀 Quick Start Summary

1. **Setup**: Configure two LBank accounts with API keys
2. **Fund**: Add USDT and tokens to both accounts
3. **Configure**: Set your trading parameters (time, spread, volume)
4. **Launch**: Start the bot through GUI or command line
5. **Monitor**: Watch the trading activity begin
6. **Manage**: Adjust parameters as needed

---

## 💬 Common Questions

**Q: Will I lose money?**
A: The bot trades at mid-prices, so theoretically you break even. However, exchange fees mean small losses over time.

**Q: How much volume can it generate?**
A: Depends on your wallet percentage and timing settings. Typically $10,000 - $100,000+ per day.

**Q: Can I run it 24/7?**
A: Yes, but use the volume pause feature to prevent excessive activity.

**Q: What if one account runs out of funds?**
A: The bot detects this and pauses trading until you add more funds.

**Q: Does it affect the actual token price?**
A: Since trades happen between your own accounts at mid-prices, it has minimal price impact.

---

## 📞 Bot Status Messages

You'll see various messages during operation:

```
✅ "Done placing orders" - Trade cycle completed successfully
⏸️ "Today's volume exceeded pause volume" - Safety limit reached
⚠️ "Account doesn't have enough USDT" - Need to add funds
🔄 "Executing no-gap trading strategy" - Using backup trading method
📊 "Spread is within acceptable range" - Normal trading conditions
```

---

## 🎓 Understanding the Results

### **Volume Created:**
Shows market activity and interest in your token

### **Trade Distribution:**
Orders appear across different price levels

### **Time Randomization:**
Trades occur at unpredictable intervals

### **Natural Patterns:**
Order sizes and timing mimic real traders

---

*This bot is a sophisticated tool for market making and volume generation. Use responsibly and in compliance with all applicable laws and regulations.*

---

**Version:** 1.0  
**Exchange:** LBank  
**Trading Type:** Volume Generation / Market Making  
**Automation Level:** Fully Automated  
