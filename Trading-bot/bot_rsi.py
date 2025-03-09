import ccxt
import pandas as pd
import ta
import time
import json
import logging
from datetime import datetime, timedelta

# Configuración de logs
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Cargar configuración
with open("config.json", "r") as file:
    config = json.load(file)

# Conectar con el exchange
exchange = getattr(ccxt, config["exchange"])({
    'apiKey': config["api_key"],
    'secret': config["api_secret"],
    'options': {'defaultType': 'spot'}
})

def fetch_data(pair, timeframe, limit=100):
    """Obtiene datos OHLCV del exchange."""
    try:
        candles = exchange.fetch_ohlcv(pair, timeframe, limit=limit)
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.info(f"📊 Datos obtenidos: {len(df)} registros.")
        return df
    except Exception as e:
        logger.error(f"❌ Error al obtener datos: {e}")
        return None

def apply_indicators(df):
    """Calcula EMA y RSI."""
    df['EMA'] = ta.trend.ema_indicator(df['close'], window=config["ema_period"])
    df['RSI'] = ta.momentum.rsi(df['close'], window=config["rsi_period"])
    logger.info(f"📈 EMA: {df['EMA'].iloc[-1]}, RSI: {df['RSI'].iloc[-1]}")
    return df

def check_signals(df):
    """Genera señales de compra/venta."""
    last_row = df.iloc[-1]
    previous_row = df.iloc[-2]

    if last_row['close'] > last_row['EMA'] and previous_row['RSI'] < 30 and last_row['RSI'] > 30:
        return 'buy'

    if last_row['close'] < last_row['EMA'] and previous_row['RSI'] > 70 and last_row['RSI'] < 70:
        return 'sell'

    return None

def place_order(signal, pair):
    """Ejecuta una orden en base a la señal."""
    try:
        balance = exchange.fetch_balance()['USDT']['free']
        
        if signal == 'buy':
            amount = balance * 0.95 / exchange.fetch_ticker(pair)['last']
            exchange.create_market_buy_order(pair, amount)
            logger.info(f"🚀 Compra ejecutada: {amount} {pair}")

        elif signal == 'sell':
            amount = exchange.fetch_balance()[pair.split('/')[0]]['free']
            exchange.create_market_sell_order(pair, amount)
            logger.info(f"🔴 Venta ejecutada: {amount} {pair}")

    except Exception as e:
        logger.error(f"❌ Error al ejecutar la orden: {e}")

def run_bot():
    """Lógica principal del bot."""
    try:
        logger.info("🤖 Iniciando el bot...")
        df = fetch_data(config["pair"], config["timeframe"])
        if df is not None:
            df = apply_indicators(df)
            signal = check_signals(df)
            logger.info(f"📡 Señal generada: {signal}")
            if signal:
                logger.info(f"🚀 Señal de {signal} detectada.")
                place_order(signal, config["pair"])
            else:
                logger.info("⏳ No hay señales en este momento.")
    except Exception as e:
        logger.error(f"❌ Error en run_bot: {e}")

# Bucle infinito
while True:
    logger.info("🔄 Ejecutando ciclo...")
    run_bot()
    time.sleep(3600)  # Ejecuta cada hora
