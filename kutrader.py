# Copyright 2021 Micah Loverro
# Loverro Software Consulting
# Permission is hereby granted, to any person obtaining a copy of this software and associated documentation files (the "Software"),
# to use or copy this software. Permission is not granted to publish, distribute, sublicense, and/or sell copies of the Software.
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF 
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR OR COPYRIGHT HOLDER BE LIABLE 
# FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. THE AUTHOR OR COPYRIGHT HOLDERS SHALL NOT BE RESPONSIBLE FOR ANY LOSS 
# OF PROPERTY OR ASSETS FROM USING THIS SOFTWARE.

#Installation:
#pip install kucoin

# Imports for builtin modules:
from collections import defaultdict
import sys, cmd
import datetime
from dateutil.parser import parse as datetime_parser
import time
import logging
logging.basicConfig(filename='detailed_info.log', level=logging.INFO, format = '%(asctime)-15s%(message)s')

high_priority_info_log = logging.getLogger('high_priority_info_log')
high_priority_info_handler = logging.FileHandler(filename='trades.log')
high_priority_info_handler.setFormatter(logging.Formatter('%(message)s'))
high_priority_info_log.addHandler(high_priority_info_handler)

low_priority_info_log = logging.getLogger('low_priority_info_log')
low_priority_info_handler = logging.FileHandler(filename='messages.log')
low_priority_info_handler.setFormatter(logging.Formatter('%(message)s'))
low_priority_info_log.addHandler(low_priority_info_handler)

from io import StringIO 
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Imports for installed modules:
from kucoin.client import Client
from kucoin.asyncio import KucoinSocketManager
from kucoin.exceptions import KucoinAPIException

# Imports for custom modules:
from display import *
from util import *

try:
    from config import *
except ModuleNotFoundError:
    print("No config.py file found.")
    quit()

class TxTrigger:
    # Types:
    MA_CROSSOVER = 'MA-CROSSOVER'

    def __init__(self, symbol, ttype, side, **kwargs):
        self.symbol = symbol
        self.type = ttype
        self.side = side
        self.kwargs = kwargs

class KucoinClient(Client):
    def __init__(self, client):
        self.client = client
        accounts = self.client.get_accounts()
        self.accounts = defaultdict(dict)
        for a in accounts:
            self.accounts[a['type']][a['currency']] = {
                 'available': float(a['available']),
                 'balance': float(a['balance']),
                 'holds': float(a['holds']),
                 'id': a['id'],
                 'time': time.time()
                 }
        time.sleep(0.001)
        symlist = self.client.get_currencies()
        self.currency_precision = dict()
        # logging.info(symlist)
        for sl in symlist:
            self.currency_precision[sl['currency']] = sl['precision']

        time.sleep(0.001)
        symbol_details = self.client.get_symbols()
        self.symbol_details = dict()
        for sd in symbol_details:
            if sd['symbol'] in SYMBOLS:
                self.symbol_details[sd['symbol']] = sd
        logging.info(f" symbol details: {self.symbol_details}")

        self.triggers = []
        # For candle data
        self.market_data = dict()
        for sym in SYMBOLS:
            self.market_data[sym] = MarketData(self.client, sym, MA_WINDOW[sym], moving_averages=(FAST_MA_PERIOD[sym], SLOW_MA_PERIOD[sym]))
        self.orderbook_data = defaultdict(dict)

        # { symbol : { 'buy': float, 'sell': float } }
        self.last_fill_price = defaultdict(lambda: defaultdict(float))

    def round_price(self, symbol, price):
        mm = incr = float(self.symbol_details[symbol]['priceIncrement'])
        return self.round(price, mm, float('Inf'), incr)
    def round_size(self, symbol, size):
        mm = float(self.symbol_details[symbol]['baseMinSize'])
        MM = float(self.symbol_details[symbol]['baseMaxSize'])
        incr = float(self.symbol_details[symbol]['baseIncrement'])
        return self.round(size, mm, MM, incr, truncate = True) 
    def round_funds(self, symbol, funds):
        mm = float(self.symbol_details[symbol]['quoteMinSize'])
        MM = float(self.symbol_details[symbol]['quoteMaxSize'])
        incr = float(self.symbol_details[symbol]['quoteIncrement'])
        return self.round(funds, mm, MM, incr)
    def round(self, value, minimum, maximum, increment, truncate = False):
        value = min(value, maximum)
        value = max(value, minimum)
        precision = float_to_ndigits(increment)
        if truncate:
            whole, frac = str(value).split('.')
            frac = frac[:precision]
            return float(f"{whole}.{frac}")
        return round(value, precision)

    def sell_all(self, symbol):
        self.cancel_all_orders(symbol)
        funds = self.round_funds(symbol, float('Inf'))
        o = self.client.create_market_order(symbol, Client.SIDE_SELL, funds = funds)
        logging.info(o)


    def buy_all(self, symbol):
        # sym = symbol.split('-')[0]
        currency = symbol.split('-')[1]
        avail = self.accounts['trade'][currency]['available']
        # rounding = self.currency_precision[currency]

        o = self.client.create_market_order(symbol, Client.SIDE_BUY, funds = avail)
        logging.info(o)

    def cancel_all_orders(self, symbol=None):
        if symbol is None: 
            info = self.client.cancel_all_orders(symbol = symbol)
            logging.info(f" Canceled order: {info}")
        else:
            o = self.client.get_orders(status='active', symbol=symbol)
            oids = [i['id'] for i in o['items']]
            for oid in oids:
                info = self.client.cancel_order(oid)
                logging.info(f" Canceled order: {info}")
    def stop(self):
        for sym in SYMBOLS:
            self.market_data[sym].stop()
    def create_market_order(self, symbol, side, size=None, funds=None, client_oid=None, remark=None, stp=None):
        return self.client.create_market_order(symbol, side, size=size, funds=funds, client_oid=client_oid, remark=remark, stp=stp)
    def set_hp_display(self, display):
        self.hp_display = display
    def set_lp_display(self, display):
        self.lp_display = display
    def pop_triggers(self):
        triggers = self.triggers
        self.triggers = []
        return triggers

    def get_account_balance(self, symbol, account_type = 'trade'):
        """ Returns the balance of the given asset in the account """
        symbol = symbol.split('-')[0]
        return float(self.accounts[account_type][symbol]['balance'])
    def get_account_value(self, symbol = None, account_type = 'trade'):
        """ Returns the value in USDT of the given asset in the account. If symbol is None, returns the total value across all assets. """
        if symbol is None:
            # Get full account value
            value = 0
            for sym in self.accounts[account_type]:
                balance = float(self.accounts[account_type][sym]['balance'])
                if sym == 'USDT':
                    sell_price = 1
                else:
                    symbol = sym + '-USDT'
                    try:
                        sell_price = float(self.orderbook_data[symbol]['bestBid'])
                    except KeyError:
                        sell_price = 0
                value += balance*sell_price
            return value
        else:
            # For a single currency
            sym = symbol.split('-')[0]
            symbol = sym + '-USDT'
            try:
                balance = float(self.accounts[account_type][sym]['balance'])
            except KeyError:
                balance = 0
            if sym == 'USDT': sell_price = 1
            else:
                try: 
                    sell_price = float(self.orderbook_data[symbol]['bestBid'])
                except KeyError:
                    sell_price = 0
            
            return balance*sell_price

    def repr_lines(self):
        lines = []
        lines.append('\t'.join(['Symbol', 'ActType', 'Balance', 'Avail', 'Value', 'Fill P.']))
        # for t in self.accounts:
            # for c in self.accounts[t]:
        # Only show data in trade accounts
        t = 'trade'
        if t in self.accounts:
            for c in self.accounts['trade']:   
                if self.accounts[t][c]['balance'] > 0:         
                    lines.append(f"{c}\t" +
                                f"{t}\t" +
                                f"{pad_or_trim(self.accounts[t][c]['balance'])}\t" +
                                f"{pad_or_trim(self.accounts[t][c]['available'])}\t" +
                                f"{pad_or_trim(self.get_account_value(symbol = c))}\t" +
                                f"{pad_or_trim(self.last_fill_price[c + '-USDT']['buy'])}") # Take care when generalizing to other markets
        lines.append('\t'.join(['Symbol',' ','Bid', 'Ask', 'Close', 'Fast MA', 'Slow MA', 'Cross']))
        for sym in SYMBOLS:
            ma = self.market_data[sym].get_last_ma(ma = WHICH_MA)
            close = self.market_data[sym].get_last_close()
            ma_crossover, first_occur = self.market_data[sym].get_ma_crossover(ma=WHICH_MA)
            if ma_crossover is not None and first_occur is True:
                self.lp_display.feedlines(f"{sym}: {WHICH_MA} crossover is {ma_crossover} at {close}")
                if ma_crossover == 'bullish': side = Client.SIDE_BUY
                elif ma_crossover == 'bearish': side = Client.SIDE_SELL
                self.triggers.append(TxTrigger(sym, TxTrigger.MA_CROSSOVER, side))
            if len(sym) >= 8: 
                num_tabs = 1
            else:
                num_tabs = 2
            try: 
                bid = self.orderbook_data[sym]['bestBid']
                ask = self.orderbook_data[sym]['bestAsk']
            except KeyError:
                bid = 0
                ask = 0
            lines.append(f"{sym}" + "\t"*num_tabs + 
                         f"{pad_or_trim(bid)}\t"
                         f"{pad_or_trim(ask)}\t"
                         f"{pad_or_trim(close)}\t" +
                         f"{pad_or_trim(ma[0])}\t" +
                         f"{pad_or_trim(ma[1])}\t" +
                         f"{ma_crossover}") 
        return lines

    async def handle_evt(self, msg):
        if msg['subject'] == 'trade.ticker':
            symbol = msg['topic'].split(':')[-1]
            self.orderbook_data[symbol] = msg['data']
            return

        logging.info(f" handle_evt: {msg}")
        try:
            assert(msg['topic'] == '/spotMarket/tradeOrders')
            assert(msg['data']['type'] == 'match')
            matchPrice = float(msg['data']['matchPrice'])
            side = msg['data']['side']
            orderType = msg['data']['orderType']
            filledSize = float(msg['data']['filledSize'])
            symbol = msg['data']['symbol']
            total = matchPrice*filledSize
            if symbol.split('-')[1].casefold() == 'usdt':
                total = '$'+str(total)
            self.hp_display.feedlines(f"Filled {orderType} {side} {symbol} {filledSize} at {matchPrice}. Total: {total}.")
            self.last_fill_price[symbol][side] = matchPrice
        except (KeyError, AssertionError):
            pass
        # finally:
        #     pass
        if msg['subject'] == 'account.balance':
            account_type = msg['data']['relationEvent'].split('.')[0]
            currency = msg['data']['currency']
            self.accounts[account_type][currency] = {
                 'available': float(msg['data']['available']),
                 'balance': float(msg['data']['total']),
                 'holds': float(msg['data']['hold']),
                 'id': msg['data']['accountId'],
                 'time': float(msg['data']['time'])
                 }
        

    async def ainit(self):
        global loop
        self.ksm_priv = await KucoinSocketManager.create(loop, self.client, self.handle_evt, private=True)
        self.ksm = await KucoinSocketManager.create(loop, self.client, self.handle_evt)
        await self.ksm_priv.subscribe('/account/balance')
        await self.ksm_priv.subscribe('/spotMarket/tradeOrders')
        self.tasks = []
        for sym in SYMBOLS:
            await self.ksm.subscribe(f'/market/ticker:{sym}')
            self.tasks.append(asyncio.create_task(self.market_data[sym].auto_update()))
        await asyncio.gather(*self.tasks)

class Trader:
    """ Class to handle trading instance """
    def __init__(self, wrapped_client):
        
        self.running = True
        self.up_since = time.time()

        self.client = wrapped_client

        # Load orders that may have been placed before this program started
        
        ## Set up the display
        self.display_heading = Display()
        self.display_grid = Display()
        self.display_high_priority_feed = TimedDisplay(num_lines = 6, priority=10)
        self.display_high_priority_feed.set_logger('high_priority_info_log')
        self.display_low_priority_feed = TimedDisplay(num_lines = 12, priority=0)
        self.display_low_priority_feed.set_logger('low_priority_info_log')
        self.display_info_feed = CombinedDisplay(
            self.display_high_priority_feed, 
            self.display_low_priority_feed, 
            max_lines=12
        )
        self.display = ConsoleInterface(
            self.display_heading,
            self.display_grid,
            self.display_info_feed
        )
        
        self.client.set_hp_display(self.display_high_priority_feed)
        self.client.set_lp_display(self.display_low_priority_feed)

        ## Load existing positions
  
    def cancel_all_orders(self, symbol=None):
        info = self.client.cancel_all_orders(symbol = symbol)
        logging.info(f" Order canceled: {info}")  
    def create_limit_order(self, symbol, side, price, size):
        price = self.client.round_price(symbol, price)
        size = self.client.round_size(symbol, size)
        logging.info(f"self.client.client.create_limit_order({symbol}, side = {side}, price = {price}, size = {size})")
        o = self.client.client.create_limit_order(symbol, side = Client.SIDE_SELL, price = price, size = size)
        print(o)
        return o

    def create_market_order(self, symbol, side, size=None, funds=None, client_oid=None, remark=None, stp=None):
        o = None
        if size is not None: size = self.client.round_size(symbol, size)
        if funds is not None: funds = self.client.round_funds(symbol, funds)
        try:
            o = self.client.create_market_order(symbol, side, size=size, funds=funds, client_oid=client_oid, remark=remark, stp=stp)
        except KucoinAPIException as e:
            logging.info(f" Tried to {side} {symbol}, but {e}.")
        print(o)
        logging.info(f" Market order: {o}")
        return o

    async def main_loop(self, sleep_time = MAIN_LOOP_SLEEP_TIME, loops = float("Inf")):
        """Main loop which calls other functions/strategies. Also handles the display."""

        # Wait to let market data load
        await asyncio.sleep(3)
        i = 0        
        while i < loops and self.running:
            self.update_display()
            triggers = self.client.pop_triggers()
            for t in triggers:
                asyncio.get_event_loop().create_task(self.handle_trigger(t))
            await asyncio.sleep(sleep_time)
            i += 1
        self.running = False

    async def handle_trigger(self, t):
        if t.type == TxTrigger.MA_CROSSOVER:
            amt = TRANSACT_AMOUNT[t.symbol]
            if t.side == Client.SIDE_SELL:
                amt = SELL_TO_BUY_RATIO[t.symbol]*TRANSACT_AMOUNT[t.symbol]
                self.cancel_all_orders(symbol = t.symbol)
                await asyncio.sleep(0.01)
            
            self.create_market_order(t.symbol, t.side, funds = amt)
            
            if t.side == Client.SIDE_BUY:
                await asyncio.sleep(2)
                self.cancel_all_orders(symbol = t.symbol)
                price = float(self.client.orderbook_data[t.symbol]['price'])*(100+TAKE_PROFIT_PERCENT[t.symbol])/100
                size = self.client.get_account_balance(symbol = t.symbol)
                self.create_limit_order(t.symbol, side = Client.SIDE_SELL, price = price, size = size)

    def update_display(self):
        horiz_line = '─'
        vert_line = '│'
        top_left_corner = '┌'
        top_right_corner = '┐'
        bot_left_corner = '└'
        bot_right_corner = '┘'
        # Heading
        line_size = 8*12
        lines = []
        lines += [f"{top_left_corner}{horiz_line*(line_size-5)}{top_right_corner}"]
        heading = f"{vert_line}{time.ctime()} │ " + \
                  f"Uptime: {datetime.timedelta(seconds = int(time.time()-self.up_since))}  │ " + \
                  f"Total Value: ${round(self.client.get_account_value(), 5)}"
        heading = heading + f"{' '*(line_size-len(heading)-4)}{vert_line}"
        lines += [heading]
        lines += [f"{bot_left_corner}{horiz_line*(line_size-5)}{bot_right_corner}"]
        self.display_heading.setlines(*lines)

        # Grid
        self.display_grid.setlines(*self.client.repr_lines())

        print(self.display)
    def stop(self):
        self.client.stop()
        self.running = False
        print("Quitting. Cleaning up...")
    async def handle_input(self):
        while self.running:
            cmd = await ainput("")
            cmd = cmd.casefold()
            if cmd == "quit":
                self.stop()
            elif cmd == "":
                self.update_display()
            elif cmd == "breakpoint":
                # pass 
                breakpoint()
            elif cmd == "test":
                pass
            elif cmd.startswith("buy") or cmd.startswith("sell"):
                cmd  = cmd.split(' ')
                def print_usage():
                    self.display_low_priority_feed.feedlines(f"Usage: {cmd[0]} symbol [$0.00]")
                    self.update_display()
                if len(cmd) == 1:
                    print_usage()
                    continue
                if cmd[0] == 'buy':
                    side = Client.SIDE_BUY
                elif cmd[0] == 'sell':
                    side = Client.SIDE_SELL
                symbol = cmd[1].upper()
                if symbol not in SYMBOLS:
                    self.display_low_priority_feed.feedlines(f"Symbol {symbol} not included in config.py")
                    self.update_display()
                    continue
                if len(cmd) == 2:
                    if side == Client.SIDE_BUY:
                        self.client.buy_all(symbol)
                    elif side == Client.SIDE_SELL:
                        self.client.sell_all(symbol)
                    continue
                funds = None
                size = None
                if len(cmd) > 2:
                    if cmd[2].startswith('$'):
                        funds = float(cmd[2][1:])
                    else:
                        size = float(cmd[2])
                else:
                    funds = TRANSACT_AMOUNT[symbol]
                self.create_market_order(symbol, side, size=size, funds=funds)
            else:
                print(f'{cmd} not yet implemented.')

async def main():
    # Set up

    client = KucoinClient(Client(api_key = API_KEY, api_secret = API_SECRET, passphrase = API_PASSPHRASE, sandbox = SANDBOX))
    trader = Trader(client)
   
    # Main loop
    print("Starting KuCoin trading bot...")
    await asyncio.gather(client.ainit(),
                         trader.main_loop(),
                         trader.handle_input())

    print("Goodbye :)")
    
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())