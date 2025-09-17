import LBank.BasicDataMan as bd
import LBank.AccountMan as ac
import LBank.new_v2_inter.WalletMan as wm
import LBank.new_v2_inter.MarketMan as mm
import LBank.new_v2_inter.OrderMan as om
import math, random, time, sched, datetime, pprint, json

class VolumeBot:
    def __init__(self, _min_time, _max_time, _wallet_percentage, _min_spread, _max_spread, _pause_volume, _buy_sell_ratio, _apikey1, _secretkey1, _apikey2, _secretkey2, _trading_pair='') -> None:
        self.min_time = _min_time
        self.max_time = _max_time
        self.wallet_percentage = _wallet_percentage/100
        self.min_spread = _min_spread
        self.max_spread = _max_spread
        assert self.max_spread > self.min_spread, f"max spread has to be larger than min spread, got max_spread = {self.max_spread}, min_spread = {self.min_spread}"
        self.pause_volume = _pause_volume
        self.buy_sell_ratio = _buy_sell_ratio

        self.account1_api_key = _apikey1
        self.account1_secret_key = _secretkey1

        self.account2_api_key = _apikey2
        self.account2_secret_key = _secretkey2
        
        # Account 1 managers
        self.accountMan1 = ac.AccountMan(self.account1_api_key, self.account1_secret_key)
        self.orderMan1 = om.OrderMan(self.account1_api_key, self.account1_secret_key)

        # Account 2 managers
        self.accountMan2=ac.AccountMan(self.account2_api_key, self.account2_secret_key)
        self.orderMan2 = om.OrderMan(self.account2_api_key, self.account2_secret_key)

        # Universal managers
        basicdataMan=bd.BaseConfigMan(self.account1_api_key, self.account1_secret_key)
        self.marketMan = mm.MarketMan(self.account1_api_key, self.account1_secret_key)

        # Set trading pair from input and normalize
        # - if missing, default to hvt_usdt
        # - append _usdt if base provided without quote
        # - lower-case for API consistency
        incoming_pair = _trading_pair or 'hvt_usdt'
        if '_' not in incoming_pair:
            incoming_pair = f'{incoming_pair}_usdt'
        self.trading_pair = incoming_pair.lower()

        ####get accuracy info######
        data = basicdataMan.getAccuracyInfo()
         # Save accuracy data to text file for debugging
        try:
            with open('lbank_accuracy_data.txt', 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("LBank Accuracy Info Debug Data\n")
                f.write(f"Timestamp: {datetime.datetime.now()}\n")
                f.write(f"Requested Trading Pair: {self.trading_pair}\n")
                f.write("="*60 + "\n\n")
                
                # Write raw response
                f.write("RAW API RESPONSE:\n")
                f.write("-"*40 + "\n")
                f.write(str(data) + "\n\n")
                
                # Write formatted JSON if possible
                try:
                    f.write("FORMATTED JSON RESPONSE:\n")
                    f.write("-"*40 + "\n")
                    f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n\n")
                except:
                    f.write("Could not format as JSON\n\n")
                
                # Write available symbols list
                f.write("AVAILABLE TRADING PAIRS:\n")
                f.write("-"*40 + "\n")
                if data and 'data' in data and isinstance(data['data'], list):
                    for i, symbol_info in enumerate(data['data'], 1):
                        symbol = symbol_info.get('symbol', 'N/A')
                        qty_acc = symbol_info.get('quantityAccuracy', 'N/A')
                        price_acc = symbol_info.get('priceAccuracy', 'N/A')
                        min_tran = symbol_info.get('minTranQua', 'N/A')
                        
                        f.write(f"{i:3d}. {symbol:<15} | Qty Acc: {qty_acc:<5} | Price Acc: {price_acc:<5} | Min Trade: {min_tran}\n")
                        
                        # Highlight HLPR-related symbols
                        if 'hvt' in symbol.lower():
                            f.write(f"     *** HVT MATCH FOUND: {symbol} ***\n")
                else:
                    f.write("No trading pairs data available or invalid format\n")
                
                f.write("\n" + "="*60 + "\n")
                f.write("Search Results for HVT:\n")
                f.write("-"*40 + "\n")
                
                if data and 'data' in data and isinstance(data['data'], list):
                    hvt_found = False
                    for symbol_info in data['data']:
                        symbol = symbol_info.get('symbol', '')
                        if 'hvt' in symbol.lower():
                            f.write(f"FOUND: {symbol}\n")
                            f.write(f"  - Quantity Accuracy: {symbol_info.get('quantityAccuracy', 'N/A')}\n")
                            f.write(f"  - Price Accuracy: {symbol_info.get('priceAccuracy', 'N/A')}\n")
                            f.write(f"  - Min Transaction: {symbol_info.get('minTranQua', 'N/A')}\n\n")
                            hvt_found = True

                    if not hvt_found:
                        f.write("No HVT-related symbols found in the response\n")

                        # Try to find similar symbols
                        f.write("\nSimilar symbols that might be related:\n")
                        for symbol_info in data['data']:
                            symbol = symbol_info.get('symbol', '')
                            if any(char in symbol.lower() for char in ['hvt', 'lpr', 'helper']):
                                f.write(f"Similar: {symbol}\n")
                else:
                    f.write("No data to search through\n")
            
            print(f"Accuracy data saved to: lbank_accuracy_data.txt")
            
        except Exception as e:
            print(f"Error saving accuracy data to file: {e}")
        

        
    # Set default values in case we don't find the trading pair
        self.quantity_accuracy = 2.0  # Default to 2 decimal places
        self.price_accuracy = 4.0     # Default to 4 decimal places
        self.min_transaction_quantity = 0.01  # Default minimum transaction
    # NOTE: Do not override self.trading_pair here; use the symbol provided/normalized above

        found_symbol = False
        try:
            if 'data' in data and data['data']:
                for i in data['data']:
                    if i['symbol'] == self.trading_pair:
                        self.quantity_accuracy = float(i['quantityAccuracy'])
                        self.price_accuracy = float(i['priceAccuracy'])
                        self.min_transaction_quantity = float(i['minTranQua'])
                        found_symbol = True
                        break
        except Exception as e:
            print(f"Error parsing accuracy info: {e}")
        
        if not found_symbol:
            print(f"WARNING: Trading pair '{self.trading_pair}' not found in accuracy info. Using default values.")
            
        print("Quantity accuracy:", self.quantity_accuracy)
        print("Price accuracy:", self.price_accuracy)

        # Get the amount to trade
        self.acc1_usdt, self.acc1_hvt, self.acc2_usdt, self.acc2_hvt = self.check_balance()
        self.acc1_usdt = self.round_nearest(self.acc1_usdt, 1/(10**self.price_accuracy))
        self.acc1_hvt = self.acc1_hvt - self.acc1_hvt%(1/(10**self.quantity_accuracy))
        self.acc2_hvt = self.acc2_hvt - self.acc2_hvt%(1/(10**self.quantity_accuracy))
        print("Acc1 USDT:", self.acc1_usdt)
        print("Acc1 HVT", self.acc1_hvt)
        print("Acc2 USDT:", self.acc2_usdt)
        print("Acc2 HVT", self.acc2_hvt)

        if self.acc1_hvt < self.acc2_hvt:
            amount_to_buy = self.wallet_percentage*self.acc1_hvt
            self.last_traded_account = 2
        else:
            amount_to_buy = self.wallet_percentage*self.acc2_hvt
            self.last_traded_account = 1
        self.quantity_to_trade = float(self.round_nearest(amount_to_buy, 1/(10**self.quantity_accuracy)))
        self.required_usdt = 0
        
    def run(self):
        """Start the loop
        """
        scheduler = sched.scheduler(time.time, time.sleep)
        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
        scheduler.run()
    
    def place_order(self, scheduler):
        """Automatically check balance and place order forward or backward

        Args:
            scheduler (sched.scheduler): scheduler object
        """
        print(datetime.datetime.now(), "Entering order placement")

        data = self.marketMan.getKline(symbol=self.trading_pair, size=20, type='day1', time=round(time.time()))
        print("Kline data:", data)
        
        # Check if API response is valid
        if not isinstance(data, dict):
            print(f"Invalid API response format: {data}")
            scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
            return
            
        # Check for API errors
        if data.get('result') == 'false':
            error_msg = data.get('msg', 'Unknown API error')
            error_code = data.get('error_code', 'Unknown')
            print(f"API Error: {error_msg} (Code: {error_code})")
            scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
            return
            
        # Check if data structure is as expected
        if 'data' not in data or not data['data'] or len(data['data']) == 0:
            print("No kline data available")
            scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
            return
            
        # Check if the data array has enough elements
        if len(data['data'][0]) < 6:
            print("Incomplete kline data structure")
            scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
            return
            
        if data['data'][0][5] > self.pause_volume:
            print("Today's volume exceeded pause volume")
            scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
            return

        hvt_orderbook = self.marketMan.getBookTicker(symbol=self.trading_pair)
        hvt_ask = float(hvt_orderbook['data']['askPrice'])
        hvt_bid = float(hvt_orderbook['data']['bidPrice'])
        mid_price = float(self.round_nearest((hvt_ask + hvt_bid)/2,1/(10**self.quantity_accuracy)))
        
        # Calculate spread as a percentage
        current_spread = hvt_ask - hvt_bid
        spread_percentage = current_spread / hvt_bid
        
        print(f"Current prices - Mid: {mid_price}, Ask: {hvt_ask}, Bid: {hvt_bid}")
        print(f"Current spread: {current_spread} ({spread_percentage:.4%})")
        
        if mid_price == hvt_bid or mid_price == hvt_ask:
            has_spread = False
            print("No spread detected - attempting alternative trading strategies")
            
            # Try no-gap trading instead of skipping
            if self.execute_no_gap_trade():
                print("Successfully executed no-gap trade")
                scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
                return
            else:
                print("No-gap trade failed, will retry shortly")
                # Shorter wait time for retry
                scheduler.enter(min(self.random_waittime_gen(), 60), 1, self.place_order, (scheduler,))
                return
        else:
            has_spread = True
            
        # Check if spread is within our min/max parameters (with your wide range, this should rarely trigger)
        if spread_percentage < self.min_spread or spread_percentage > self.max_spread:
            print(f"Spread {spread_percentage:.4%} is outside desired range ({self.min_spread:.4%} - {self.max_spread:.4%})")
            
            # With your wide spread range (0.0001 to 1000000), this should almost never happen
            # But if it does, try no-gap trading as fallback
            if self.execute_no_gap_trade():
                print("Executed fallback no-gap trade due to spread issue")
            else:
                print("All trading strategies failed, retrying in 30 seconds")
                scheduler.enter(30, 1, self.place_order, (scheduler,))
                return
        
        # Continue with normal trading logic
        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
        return

        # Get account balances
        self.acc1_usdt, self.acc1_hvt, self.acc2_usdt, self.acc2_hvt = self.check_balance()
        self.acc1_usdt = self.round_nearest(self.acc1_usdt, 1/(10**self.price_accuracy))
        self.acc1_hvt = self.acc1_hvt - self.acc1_hvt%(1/(10**self.quantity_accuracy))
        self.acc2_hvt = self.acc2_hvt - self.acc2_hvt%(1/(10**self.quantity_accuracy))
        print("Acc1 USDT:", self.acc1_usdt)
        print("Acc1 HVT", self.acc1_hvt)
        print("Acc2 USDT:", self.acc2_usdt)
        print("Acc2 HVT", self.acc2_hvt)

        if has_spread:
            if self.last_traded_account == 2:
                # Order broken down into chunks
                decomposition = self.decomposition()
                temporary = 0.0
                for i in decomposition[:-1]:
                    quantity = str(self.round_nearest((self.quantity_to_trade*i), 1/(10**self.quantity_accuracy)))
                    temporary += float(quantity)
                    if quantity == '0.0':
                        continue
                    price = self.get_mid_price_random()

                    # Assuring account balance
                    self.required_usdt = (self.quantity_to_trade*price)*1.01
                    if self.acc2_usdt < self.required_usdt:
                        print("Account 2 doesn't have enough USDT, please top up")
                        print("Required amount:", self.required_usdt, "Actual amount:", self.acc2_usdt, "Top up amount:", self.required_usdt-self.acc2_usdt)
                        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
                        return
                    self.forward_trade(price, quantity)
                    time.sleep(self.random_waittime_gen())
                if self.quantity_to_trade - float(temporary) > 0.0:
                    price = self.get_mid_price_random()

                    # Assuring account balance
                    self.required_usdt = (self.quantity_to_trade*price)*1.01
                    if self.acc2_usdt < self.required_usdt:
                        print("Account 2 doesn't have enough USDT, please top up")
                        print("Required amount:", self.required_usdt, "Actual amount:", self.acc2_usdt, "Top up amount:", self.required_usdt-self.acc2_usdt)
                        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
                        return
                    self.forward_trade(price, str(self.round_nearest(self.quantity_to_trade - float(temporary), 1/(10**self.quantity_accuracy))))
                self.last_traded_account = 1
        
            elif self.last_traded_account == 1:
                decomposition = self.decomposition()
                temporary = 0.0
                for i in decomposition[:-1]:
                    quantity = str(self.round_nearest((self.quantity_to_trade*i), 1/(10**self.quantity_accuracy)))
                    temporary += float(quantity)
                    if quantity == '0.0':
                        continue
                    price = self.get_mid_price_random()

                    # Assuring account balance
                    self.required_usdt = (self.quantity_to_trade*price)*1.01
                    if self.acc2_usdt < self.required_usdt:
                        print("Account 1 doesn't have enough USDT, please top up")
                        print("Required amount:", self.required_usdt, "Actual amount:", self.acc1_usdt, "Top up amount:", self.required_usdt-self.acc1_usdt)
                        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
                        return
                    self.backward_trade(price, quantity)
                    time.sleep(self.random_waittime_gen())
                if self.quantity_to_trade - float(temporary) > 0.0:
                    price = self.get_mid_price_random()

                    # Assuring account balance
                    self.required_usdt = (self.quantity_to_trade*price)*1.01
                    if self.acc2_usdt < self.required_usdt:
                        print("Account 1 doesn't have enough USDT, please top up")
                        print("Required amount:", self.required_usdt, "Actual amount:", self.acc1_usdt, "Top up amount:", self.required_usdt-self.acc1_usdt)
                        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
                        return
                    self.backward_trade(price, str(self.round_nearest(self.quantity_to_trade - float(temporary), 1/(10**self.quantity_accuracy))))
                self.last_traded_account = 2
        
        if not has_spread:
            # This should not reach here anymore since we handle no-spread earlier
            print("Unexpected no-spread condition - executing backup strategy")
            if self.execute_no_gap_trade():
                print("Backup no-gap trade successful")
            else:
                print("All strategies failed, retrying in 30 seconds")
                scheduler.enter(30, 1, self.place_order, (scheduler,))
                return
        
        print("Done placing orders")
        scheduler.enter(self.random_waittime_gen(), 1, self.place_order, (scheduler,))
    
    def get_mid_price_random(self):
        """Get a random price between bid and ask with gap detection

        Returns:
            mid_price (float): random price between bid and ask
        """
        hvt_orderbook = self.marketMan.getBookTicker(symbol=self.trading_pair)
        hvt_ask = float(hvt_orderbook['data']['askPrice'])
        hvt_bid = float(hvt_orderbook['data']['bidPrice'])
        
        # Calculate the minimum price increment
        min_price_increment = 1/(10**self.price_accuracy)
        
        # Check if there's any gap for trading
        price_gap = hvt_ask - hvt_bid
        
        if price_gap <= min_price_increment:
            # No gap for trading - create artificial gap by adjusting prices
            print(f"No trading gap detected. Bid: {hvt_bid}, Ask: {hvt_ask}, Gap: {price_gap}")
            
            # Create small gap by moving slightly away from current prices
            adjustment = min_price_increment * 2
            
            # Randomly choose to trade closer to bid or ask
            if random.random() < 0.5:
                # Trade closer to bid (buying pressure)
                mid_price = self.round_nearest(hvt_bid + adjustment, min_price_increment)
            else:
                # Trade closer to ask (selling pressure)
                mid_price = self.round_nearest(hvt_ask - adjustment, min_price_increment)
                
            print(f"🎯 Created artificial trading gap at price: {mid_price}")
            return mid_price
        
        # Normal case - there's a gap for trading
        mid_price = hvt_ask
        max_attempts = 50  # Prevent infinite loop
        attempts = 0
        
        while (mid_price == hvt_ask or mid_price == hvt_bid) and attempts < max_attempts:
            mid_price = self.round_nearest(random.uniform(hvt_bid, hvt_ask), min_price_increment)
            attempts += 1
            
        # If still no valid mid price found, force one
        if mid_price == hvt_ask or mid_price == hvt_bid:
            mid_price = self.round_nearest((hvt_bid + hvt_ask) / 2, min_price_increment)
            print(f"🔧 Forced mid-price calculation: {mid_price}")
            
        return mid_price
    
    def cummulative_amount_price(self, quantity):
        """Generate the price needed to fulfill the entire order according to the order book

        Args:
            quantity (float): The required amount to be filled

        Returns:
            price (float): the price where the whole position is guaranteed to be filled
        """
        market_depth = self.marketMan.getDepth(symbol=self.trading_pair, size=60)
        # print("market depth")
        # pprint.pprint(market_depth)
        
        cumulative_amount = 0.0
        for i in market_depth['data']['asks']:
            cumulative_amount += float(i[1])
            if cumulative_amount > float(quantity):
                ask_price = i[0]
                break
        
        cumulative_amount = 0.0
        for i in market_depth['data']['bids']:
            cumulative_amount += float(i[1])
            if cumulative_amount > float(quantity):
                bid_price = i[0]
                break
        return ask_price, bid_price
    
    def forward_trade(self, price, quantity):
        """Function to make a forward trade i.e. account 1 sell and account 2 buy

        Args:
            price (float): mid price
            quantity (float): quantity to buy/sell
        """
        print("Forward trade:")
        print(price, quantity)
        if random.random() < self.buy_sell_ratio:
            # Appear as buy order
            print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='sell', price=str(price), amount=str(quantity), custom_id=''))
            print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='buy', price=str(price), amount=str(quantity), custom_id=''))
        else:
            # Appear as sell order
            print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='buy', price=str(price), amount=str(quantity), custom_id=''))
            print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='sell', price=str(price), amount=str(quantity), custom_id=''))
    
    def backward_trade(self, price, quantity):
        """Function to make a forward trade i.e. account 2 sell and account 1 buy

        Args:
            price (float): mid price
            quantity (float): quantity to buy/sell
        """
        print("Backward trade:")
        print(price, quantity)
        if random.random() < self.buy_sell_ratio:
            # Appear as buy order
            print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='sell', price=str(price), amount=str(quantity), custom_id=''))
            print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='buy', price=str(price), amount=str(quantity), custom_id=''))
        else:
            # Appear as sell order
            print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='buy', price=str(price), amount=str(quantity), custom_id=''))
            print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='sell', price=str(price), amount=str(quantity), custom_id=''))
    
    def cancel_pending_order(self):
        """Cancel all pending orders of both accounts
        """
        self.orderMan1.getCancel_order_by_symbol(symbol=self.trading_pair)
        self.orderMan2.getCancel_order_by_symbol(symbol=self.trading_pair)
    
    def check_balance(self):
        """Check the USDT and HVT balance of both accounts
        """
        # Extract base token name from trading pair (e.g., 'hvt' from 'hvt_usdt')
        base_token = self.trading_pair.split('_')[0]
        quote_token = self.trading_pair.split('_')[1]
        
        try:
            # Account 1
            acc1_data = self.accountMan1.getUserInfo()
            if 'data' not in acc1_data or 'free' not in acc1_data['data']:
                print(f"Error: Invalid response format from API for Account 1: {acc1_data}")
                return 0.0, 0.0, 0.0, 0.0
                
            # Get balances with safe access using .get() method
            acc1_usdt = float(acc1_data['data']['free'].get(quote_token, 0))
            acc1_hvt = self.round_nearest(float(acc1_data['data']['free'].get(base_token, 0)), 1/(10**self.price_accuracy))
            print(f"Account 1 balances - {quote_token.upper()}: {acc1_usdt}, {base_token.upper()}: {acc1_hvt}")
        except Exception as e:
            print(f"Error getting Account 1 balance: {e}")
            acc1_usdt = 0.0
            acc1_hvt = 0.0

        try:
            # Account 2
            acc2_data = self.accountMan2.getUserInfo()
            if 'data' not in acc2_data or 'free' not in acc2_data['data']:
                print(f"Error: Invalid response format from API for Account 2: {acc2_data}")
                return acc1_usdt, acc1_hvt, 0.0, 0.0
                
            acc2_usdt = float(acc2_data['data']['free'].get(quote_token, 0))
            acc2_hvt = self.round_nearest(float(acc2_data['data']['free'].get(base_token, 0)), 1/(10**self.price_accuracy))
            print(f"Account 2 balances - {quote_token.upper()}: {acc2_usdt}, {base_token.upper()}: {acc2_hvt}")
        except Exception as e:
            print(f"Error getting Account 2 balance: {e}")
            acc2_usdt = 0.0
            acc2_hvt = 0.0

        return acc1_usdt, acc1_hvt, acc2_usdt, acc2_hvt
    
    def round_nearest(self, x, a):
        """Round x to nearest a. For example, x = 5.37436 and a = 0.025, then result will be 5.375
        """
        max_frac_digits = 100
        for i in range(max_frac_digits):
            if round(a, -int(math.floor(math.log10(a))) + i) == a:
                frac_digits = -int(math.floor(math.log10(a))) + i
                break
        return round(round(x / a) * a, frac_digits)

    def random_waittime_gen(self):
        """Generate a random time between min wait time and max wait time
        """
        return random.uniform(self.min_time, self.max_time)
    
    def decomposition(self, i = 20):
        """Decompose a number into random chunks, maximum 5 chunks. Used to decompose an order into smaller orders so it look more like human behavior

        Args:
            i (int, optional): Splitting number, the more, the finer the chunks. Defaults to 20.

        Returns:
            result: list of chunk in percentages, e.g. [0.2, 0.45, 0.35]
        """
        result = []
        len = random.randint(1,4)
        for j in range(len):
            if i > 0:
                n = random.randint(1, i)
                result.append(n/20)
                i -= n
        if i > 0:
            result.append(i/20)
        return result
    
    def execute_no_gap_trade(self):
        """Execute trade when there's no price gap available"""
        try:
            print("Executing no-gap trading strategy...")
            
            # Get current orderbook
            hvt_orderbook = self.marketMan.getBookTicker(symbol=self.trading_pair)
            hvt_ask = float(hvt_orderbook['data']['askPrice'])
            hvt_bid = float(hvt_orderbook['data']['bidPrice'])
            
            # Use minimum trading quantity to minimize impact
            min_quantity = str(self.min_transaction_quantity)
            
            # Strategy 1: Market taking - trade at existing prices
            if random.random() < 0.5:
                # Account 1 buys at ask price, Account 2 sells at bid price
                print(f"📈 Market taking strategy: Buy at {hvt_ask}, Sell at {hvt_bid}")
                
                if self.last_traded_account == 2:
                    print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='buy', price=str(hvt_ask), amount=min_quantity, custom_id=''))
                    time.sleep(1)  # Small delay
                    print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='sell', price=str(hvt_bid), amount=min_quantity, custom_id=''))
                    self.last_traded_account = 1
                else:
                    print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='buy', price=str(hvt_ask), amount=min_quantity, custom_id=''))
                    time.sleep(1)  # Small delay
                    print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='sell', price=str(hvt_bid), amount=min_quantity, custom_id=''))
                    self.last_traded_account = 2
            else:
                # Strategy 2: Create new price levels slightly outside current range
                price_increment = 1/(10**self.price_accuracy)
                new_bid = self.round_nearest(hvt_bid - price_increment, price_increment)
                new_ask = self.round_nearest(hvt_ask + price_increment, price_increment)
                
                print(f"📊 Creating new price levels: New Bid {new_bid}, New Ask {new_ask}")
                
                if self.last_traded_account == 2:
                    # Place orders at new price levels
                    print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='buy', price=str(new_bid), amount=min_quantity, custom_id=''))
                    time.sleep(1)  # Small delay
                    print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='sell', price=str(new_ask), amount=min_quantity, custom_id=''))
                    self.last_traded_account = 1
                else:
                    print(self.orderMan2.getCreate_order(symbol=self.trading_pair, type='buy', price=str(new_bid), amount=min_quantity, custom_id=''))
                    time.sleep(1)  # Small delay  
                    print(self.orderMan1.getCreate_order(symbol=self.trading_pair, type='sell', price=str(new_ask), amount=min_quantity, custom_id=''))
                    self.last_traded_account = 2
                    
            print("✅ No-gap trade executed successfully")
            return True
            
        except Exception as e:
            print(f"No-gap trade failed: {str(e)}")
            return False
