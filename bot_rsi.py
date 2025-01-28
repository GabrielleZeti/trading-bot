import ccxt
import pandas as pd
import ta
import time
import logging
import json

# Cargar configuración desde config.json
with open('config.json') as config_file:
    config = json.load(config_file)

API_KEY = config["api_key"]
API_SECRET = config["api_secret"]
EXCHANGE = config["exchange"]

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
    """Obtiene datos OHLCV del exchange con manejo de errores."""
    try:
        candles = exchange.fetch_ohlcv(pair, timeframe, limit=limit)
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error obteniendo datos del exchange: {e}")
        return None

def apply_indicators(df):
    """Calcula EMA y RSI."""
    df['EMA'] = ta.trend.ema_indicator(df['close'], window=EMA_PERIOD)
    df['RSI'] = ta.momentum.rsi(df['close'], window=RSI_PERIOD)
    return df

def check_signals(df):
    """Genera señales de compra/venta."""
    if df is None or df.empty:
        logger.warning("No se pudo obtener datos del exchange.")
        return None

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
    """Ejecuta una orden en base a la señal con Stop Loss y Take Profit."""
    if signal == 'buy':
        last_price = exchange.fetch_ticker(pair)['last']
        amount = balance * 0.95 / last_price

        order = exchange.create_market_buy_order(pair, amount)
        logger.info(f"Compra ejecutada: {amount} {pair} a {last_price}")

        # Establecer Stop Loss y Take Profit
        stop_loss_price = last_price * (1 - STOP_LOSS_PERCENT)
        take_profit_price = last_price * (1 + TAKE_PROFIT_PERCENT)
        logger.info(f"Stop Loss: {stop_loss_price}, Take Profit: {take_profit_price}")

    elif signal == 'sell':
        last_price = exchange.fetch_ticker(pair)['last']
        order = exchange.create_market_sell_order(pair, balance)
        logger.info(f"Venta ejecutada: {balance} {pair} a {last_price}")

def run_bot(balance):
    """Lógica principal del bot."""
    logger.info("Ejecutando el bot...")
    df = fetch_data(PAIR, TIMEFRAME)
    df = apply_indicators(df)
    signal = check_signals(df)

    if signal:
        place_order(signal, PAIR, balance)

# Bucle infinito con optimización de balance
balance = exchange.fetch_balance()['USDT']['free']
counter = 0  # Contador de ejecuciones

while True:
    try:
        if counter % 10 == 0:  # Cada 10 ejecuciones actualiza el balance
            balance = exchange.fetch_balance()['USDT']['free']

        run_bot(balance)
        counter += 1
        time.sleep(3600)  # Ejecuta cada hora

    except Exception as e:
        logger.error(f"Error: {e}")
        time.sleep(60)
