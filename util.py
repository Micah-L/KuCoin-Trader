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

import asyncio
from collections import defaultdict, deque
import time
from concurrent.futures import ThreadPoolExecutor
# Constants
window_to_sec = {
    '1min': 60,
    '3min': 3*60, 
    '5min': 5*60, 
    '15min': 15*60, 
    '30min': 30*60, 
    '1hour': 3600, 
    '2hour': 2*3600 , 
    '4hour': 4*3600, 
    '6hour': 6*3600, 
    '8hour': 8*3600, 
    '12hour': 12*3600, 
    '1day': 24*3600, 
    '1week': 7*24*3600
}

# Useful functions
def RSI(prices, period, current_only=False):
    """ Calculate RSI and return the values as a pandas DataFrame.
    
    prices -- should be a pandas DataFrame containing price info
    current_only -- set this to True to just return the most recent value of the RSI
    """
    
    # Get the price changes
    delta = prices.diff()
    
    # Get rid of the first entry, which is NaN
    delta = delta[1:] 
    
    up, down = delta.copy(), delta.copy()
    # List of only upward moves (replace downward moves with 0)
    up[up < 0] = 0
    # List of only downward moves (replace upward moves with 0)
    down[down > 0] = 0
    
    # Calculate EMA of upward and downward moves
    roll_up1 = up.ewm(span=period).mean()
    roll_down1 = down.abs().ewm(span=period).mean()
    
    # Relative Strength
    try:
        rs = roll_up1 / roll_down1
    except ZeroDivisionError:
        # RSI is 100 if all up moves...
        rs = float("Inf")
    # Finally...
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    if current_only:
        # Just return most recent RSI value
        # print(rsi)
        return rsi.iloc[-1]
    # Returns a list of RSI values
    return rsi
def float_to_ndigits(f):
    """ Returns the number of digits after the decimal point """
    if f == int(f): return 0
    return len(str(f).split('.')[-1])
def trim_float(f):
    """ returns a trimmed string from a float:
        4.20000000000000000 -> 4.2 """
    return str(f).rstrip('0').rstrip('.')
def approx_equal(f1, f2, tolerance=0.001):
    if abs(f1 - f2) <= min(f1,f2)*tolerance:
        return True


async def ainput(prompt: str = "") -> str:
    with ThreadPoolExecutor(1, "AsyncInput") as executor:
        return await asyncio.get_event_loop().run_in_executor(executor, input, prompt)

class Capturing(list):
    """Capture stdout and save it as a variable. Usage:
    with Capturing() as output:
        do_something(my_object)"""
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

class smartdict(dict):
    """ A dict d initialized with a dict D or callable C,
        whose default value for d[k] is D[k] or C(k), respectively. """
    def __init__(self, defaults):
        self.defaults = defaults
    def __missing__(self, key):
        if callable(self.defaults):
            return self.defaults(key)
        else:
            return self.defaults[key]

def pad_or_trim(f: float, max_size = 7):
    try:
        f = float(f)
    except TypeError:
        return None
    return f'{f:.{max_size}f}'[:max_size]        
    # leng = len(f)
    # lendec = len(str(f).split('.')[1])
    # precision = lendec + max_size - leng if leng <= max_size + 1 else lendec - leng + max_size
    # final_str = f"{float(f):.{precision}f}"[:max_size]
    # return final_str
class MarketData:
    # Adapted for KuCoin kline data
    def __init__(self, client, symbol: str, candle_period: str, moving_averages = (20, 50), update_on_create = True):
        # internal data = [ [time, open, close, high, low, amount, volume, [sma1, sma2], [ema1, ema2]], ... ]
        # data is ordered with latest time first
        self.max_history = 4*max(moving_averages)
        self.data = deque()

        self.ma_periods = moving_averages
        self.symbol = symbol
        self.candle_period = candle_period
        self.window_seconds = window_to_sec[candle_period]
        
        self.client = client
        if update_on_create: self.update()
        self.auto_updating = False
        # Store the last time that a crossover was detected (i.e. get_ma_crossover() was called with a positive result)
        self.last_cross_time = {'SMA': 0, 'EMA': 0}
    def stop(self):
        self.auto_updating = False
    def get_ma_crossover(self, ma='SMA'):
        """ Returns 'bullish', 'bearish' or None depending on the moving average crossover.
         If the return value is not None, it returns a second value of True or False depending if this is the 
        first time this result has been polled on this candle. """
        ma = ma.upper()
        assert(ma in {'SMA', 'EMA'})
        ma_idx = 7
        if ma == 'SMA':
            ma_idx = 7
        elif ma == 'EMA':
            ma_idx = 8
        try:
            this_fast_ma = self.data[0][ma_idx][0]
            this_slow_ma = self.data[0][ma_idx][1]
            last_fast_ma = self.data[1][ma_idx][0]
            last_slow_ma = self.data[1][ma_idx][1]
        except IndexError:
            return None, None
        retval = None
        if last_fast_ma <= last_slow_ma and this_fast_ma > this_slow_ma:
            retval = 'bullish'
        elif last_fast_ma >= last_slow_ma and this_fast_ma < this_slow_ma:
            retval = 'bearish'
        first_occur = None
        if retval is not None:
            if self.last_cross_time[ma] != self._last_time():
                first_occur = True
                self.last_cross_time[ma] = self._last_time()
            else: first_occur = False
        return retval, first_occur

    def get_last_close(self):
        if len(self.data) > 0:
            return self.data[0][2]
        else:
            return None
    def get_last_ma(self, ma = 'SMA'):
        ma = ma.upper()
        assert(ma in {'SMA', 'EMA'})
        if ma == 'SMA': ma_idx = 7
        elif ma == 'EMA': ma_idx = 8
        try:
            return self.data[0][ma_idx]
        except IndexError:
            return [None]*len(self.ma_periods)
    async def auto_update(self, wait=True):
        self.auto_updating = True
        if not wait:
            self.update()
        while self.auto_updating:
            await asyncio.sleep( self.window_seconds*0.75 )
            self.update()
    def update(self):
        if self._last_time() is None:
            new_frames = self.max_history
        else:
            new_frames = (time.time() - self._last_time()) // self.window_seconds
        if new_frames >= 1:
            new_frames = min(self.max_history, new_frames)
            data = self._get_kline_data(new_frames)
            self._feed_data(data)
    def _trim_data(self):
        self.data.reverse()
        self.data = deque( deque(self.data, maxlen = self.max_history) )
        self.data.reverse()
    def _get_kline_data(self, candle_quantity: int):
        candle_quantity = int(candle_quantity)
        now = int(time.time())
        start = now - candle_quantity*self.window_seconds
        # print(f"data = self.client.get_kline_data({self.symbol}, kline_type = {self.candle_period}, start = {start})")
        data = self.client.get_kline_data(self.symbol, kline_type = self.candle_period, start = start)

        if len(data) < candle_quantity:
            try:
                now = int(data[0][0])
                start = now - candle_quantity*self.window_seconds
            except IndexError:
                start = None
            finally:
                data = self.client.get_kline_data(self.symbol, kline_type = self.candle_period, start = start)
        # assert(len(data) >= candle_quantity)
        return data[:candle_quantity]

    def _last_time(self):
        """ returns the timestamp of the latest frame in self.data """
        if len(self.data) > 0:
            return int(self.data[0][0])
        else:
            return None
    def _feed_data(self, data):
        # data = [ [time, open, close, high, low, amount, volume], ... ]
        # data is ordered with latest time first
        old_frames = len(self.data)
        new_frames = 0
        if data is None or len(data) == 0:
            return
        # Update the internal data
        if len(self.data) == 0:
            self.data.extendleft(data[::-1])
            new_frames = len(data)
        else:
            new_frames = (int(data[0][0]) - int(self.data[0][0])) // self.window_seconds
            self.data.extendleft(data[:new_frames][::-1])

        # Update MAs
        if old_frames > 0:
            # Start at the oldest new frame
            start_idx = new_frames - 1
        else:
            # If no old frames, start at the second oldest new frame
            start_idx = len(self.data) - 2
        sma_index = 7
        ema_index = 8
        for i in range(start_idx, -1, -1):
            this_sma = [None]*len(self.ma_periods)
            this_ema = [None]*len(self.ma_periods)
            this_value = float(self.data[i][2])
            # Calculate SMA
            for ma_idx, ma_period in enumerate(self.ma_periods):
                if len(self.data[i+1]) > 7 and self.data[i+1][sma_index][ma_idx] is not None:
                    # Check if prev SMA exists and use formula:
                    # sma[k] = ( sma[k+1] * N + a[k+1] - a[k + N] )/N
                    this_sma[ma_idx] = ( float(self.data[i+1][sma_index][ma_idx])*ma_period + this_value - float(self.data[i + ma_period ][2]) ) / ma_period
                else:
                    # Check if we have enough frames to calculate SMA from scratch
                    prev_frames = len(self.data) - 1 - i
                    if prev_frames + 1 >= ma_period:
                        this_sma[ma_idx] = sum([float(self.data[j][2]) for j in range(i, i + ma_period)])/ma_period
            assert(len(self.data[i]) == 7)
            self.data[i].append(tuple(this_sma))
            # Calculate EMA
            for ma_idx, ma_period in enumerate(self.ma_periods):
                # If prev SMA/EMA exists, use formula:
                if len(self.data[i+1]) > 7 and self.data[i+1][sma_index][ma_idx] is not None:
                    prev_ema = float(self.data[i+1][sma_index][ma_idx])
                    if len(self.data[i+1]) > 8 and self.data[i+1][ema_index][ma_idx] is not None:
                        prev_ema = float(self.data[i+1][ema_index][ma_idx])
                    alpha = 2/(1+ma_period)
                    this_ema[ma_idx] = this_value*alpha + prev_ema*(1-alpha)
            self.data[i].append(tuple(this_ema))

        self._trim_data()

class Trade:
    def __init__(self, side, quantity, price):
        self.side = side
        self.quantity = quantity
        self.price = price

        self.cost_basis = quantity * price
        if side == 'sell': self.cost_basis = -1*self.cost_basis
class TradeStack:
    def __init__(self, quantity = 0, cost_basis = 0):
        self.quantity = quantity
        self.cost_basis = cost_basis
    def push(self, trade: Trade):
        if trade.side == 'buy':
            q = self.quantity + trade.quantity
        elif trade.side == 'sell':
            q = self.quantity - trade.quantity
        self.cost_basis += trade.cost_basis
        assert(q >= 0)
        self.quantity = q
    def get_pnl(self, current_price, as_percent = False):
        value = self.quantity*current_price
        profit = value - self.cost_basis
        if as_percent: return (profit / self.cost_basis)*100
        else: return profit