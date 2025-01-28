import ccxt
import pandas as pd
import ta
import time
import logging

# Configuración del bot
API_KEY = 'ULjIfABTBLUAT8zwKuHzXwYYibXQ39c6xRClYa7gdDDu2pkxpXKDafg8V7PfXUKu'
API_SECRET = 'V98L1mg1rubEI1LJlXeNmLrjlGVy4h15F3BmehRjEPzx0BQZiO99ChYIVADmPBEV'
EXCHANGE = 'binance'  # Cambia según tu exchange
PAIR = 'BTC/USDT'  # Par a operar
TIMEFRAME = '1h'  # Temporalidad
RSI_PERIOD = 14
EMA_PERIOD = 50
STOP_LOSS_PERCENT = 0.02  # 2%
TAKE_PROFIT_PERCENT = 0.04  # 4%

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger()

# Conectar con el exchange
exchange = getattr(ccxt, EXCHANGE)({
    'apiKey': API_KEY,
    'secret': API_SECRET,
})

def fetch_data(pair, timeframe, limit=100):
    """Obtiene datos OHLCV del exchange."""
    candles = exchange.fetch_ohlcv(pair, timeframe, limit=limit)
    df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def apply_indicators(df):
    """Calcula EMA y RSI."""
    df['EMA'] = ta.trend.ema_indicator(df['close'], window=EMA_PERIOD)
    df['RSI'] = ta.momentum.rsi(df['close'], window=RSI_PERIOD)
    return df

def check_signals(df):
    """Genera señales de compra/venta."""
    last_row = df.iloc[-1]
    previous_row = df.iloc[-2]

    # Condición de compra
    if last_row['close'] > last_row['EMA'] and previous_row['RSI'] < 30 and last_row['RSI'] > 30:
        return 'buy'

    # Condición de venta
    if last_row['close'] < last_row['EMA'] and previous_row['RSI'] > 70 and last_row['RSI'] < 70:
        return 'sell'

    return None

def place_order(signal, pair, balance):
    """Ejecuta una orden en base a la señal."""
    if signal == 'buy':
        amount = balance * 0.95 / exchange.fetch_ticker(pair)['last']
        exchange.create_market_buy_order(pair, amount)
        logger.info(f"Compra ejecutada: {amount} de {pair}")

    elif signal == 'sell':
        amount = balance
        exchange.create_market_sell_order(pair, amount)
        logger.info(f"Venta ejecutada: {amount} de {pair}")

def run_bot():
    """Lógica principal del bot."""
    logger.info("Iniciando el bot...")
    balance = exchange.fetch_balance()['USDT']['free']  # Ajustar según el par base
    df = fetch_data(PAIR, TIMEFRAME)
    df = apply_indicators(df)
    signal = check_signals(df)

    if signal:
        place_order(signal, PAIR, balance)

# Bucle infinito
while True:
    try:
        run_bot()
        time.sleep(3600)  # Ejecuta cada hora
    except Exception as e:
        logger.error(f"Error: {e}")
        time.sleep(60)