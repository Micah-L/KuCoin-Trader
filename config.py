from collections import defaultdict

# The variables in this file may be changed to specify the settings for this program.
# Lines that start with a # are comments and will be ignored by the program.

### Authentication related settings
# Set true to use the sandbox mode (paper money)
# Only certain markets are supported in sandbox mode.
SANDBOX = False

if SANDBOX:
    # Credentials for KuCoin sandbox:
    API_PASSPHRASE = "your-passphrase-here"
    API_KEY = "your-api-key-here"
    API_SECRET = "your-api-secret-here"

    SYMBOLS = [
        'BTC-USDT',
    ]
else:
    # Credentials for KuCoin live trading:
    API_PASSPHRASE = "your-passphrase-here"
    API_KEY = "your-api-key-here"
    API_SECRET = "your-api-secret-here"
        
    SYMBOLS = [
        'BTC-USDT',
        'ETH-USDT',
        'ETH-BTC',
        'KCS-USDT',
        'KCS-BTC',
        'DOT-USDT',
        'DOT-BTC',
        'ADA-USDT',
        'ADA-BTC',
        'XRP-USDT',
        'XRP-BTC',
        'LTC-USDT',
        'LTC-BTC',
        'VET-USDT',
        'BCH-USDT',
        'LUNA-USDT',
        'BNB-USDT',
        'EOS-USDT',
        'NEO-USDT',
        'DASH-USDT',
        'CRO-USDT',
    ]
    # Only USDT supported right now
    syms = []
    for s in SYMBOLS:
        if s.split('-')[1] == 'USDT':
            syms.append(s)
    SYMBOLS = syms
### General settings

# Time in seconds to sleep between refreshing the display
MAIN_LOOP_SLEEP_TIME = 12

### Strategy related settings

## 
# Choose one of SMA or EMA for calculation of Moving Average Crossover
WHICH_MA = 'EMA' 
assert(WHICH_MA in ['SMA', 'EMA'])

allowed_candle_windows = ['1min', '3min', '5min', '15min', '30min', '1hour', '2hour', '4hour', '6hour', '8hour', '12hour', '1day', '1week']
## Defaults
default_fast_ma_period = 20
default_slow_ma_period = 50
default_ma_window = '1min'
default_sell_to_buy_ratio = 4 # sell orders will try to sell up to this times the transaction amount
default_transaction_amount = 5 # in dollars
default_take_profit_percent = 10

## Dictionary setup
FAST_MA_PERIOD = defaultdict(lambda: default_fast_ma_period)
SLOW_MA_PERIOD = defaultdict(lambda: default_slow_ma_period)
MA_WINDOW = defaultdict(lambda: default_ma_window)
SELL_TO_BUY_RATIO = defaultdict(lambda: default_sell_to_buy_ratio)
TRANSACT_AMOUNT = defaultdict(lambda: default_transaction_amount)
TAKE_PROFIT_PERCENT = defaultdict(lambda: default_take_profit_percent)
## Overrides
# You may override the defaults for the fast and slow MA periods.
# For example, to set the fast ma period of BTC to 10:
FAST_MA_PERIOD['BTC-USDT'] = 20
# To set the slow moving average period of 'ETH-BTC' to 75:
SLOW_MA_PERIOD['BTC-USDT'] = 50
# To change the candle size for the calculation of a particular market:
MA_WINDOW['BTC-USDT'] = '15min'

TRANSACT_AMOUNT['BTC-USDT'] = 10
SELL_TO_BUY_RATIO['BTC-USDT'] = 1

# Safety checks:
assert(default_ma_window in allowed_candle_windows)
for symbol in MA_WINDOW:
    assert(MA_WINDOW[symbol] in allowed_candle_windows)