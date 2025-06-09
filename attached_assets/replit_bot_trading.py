
import ccxt
import pandas as pd
import time
import requests
from ta.volatility import AverageTrueRange
from ta.trend import EMAIndicator

bot_token = "7274514132:AAFdt_Vr48MyKmJigy0WSNWrkgy6LWB1LI4"
chat_id = 5253696321

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

def fetch_ohlcv():
    exchange = ccxt.binance()
    data = exchange.fetch_ohlcv('BTC/USDT', timeframe='15m', limit=100)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def check_signal():
    df = fetch_ohlcv()
    df['ema_13'] = EMAIndicator(close=df['close'], window=13).ema_indicator()
    df['ema_55'] = EMAIndicator(close=df['close'], window=55).ema_indicator()
    df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    print(f"[{pd.Timestamp.now()}] Revisando señal...")

    if prev['ema_13'] < prev['ema_55'] and last['ema_13'] > last['ema_55']:
        entry = last['close']
        sl = entry - last['atr']
        tp = entry + 2 * last['atr']
        message = (
            "📈 *Señal de COMPRA (LONG)*\n"
            f"🔹 Precio actual: {entry:.2f}\n"
            f"🔹 EMA 13 cruzó sobre EMA 55\n"
            f"🔹 SL: {sl:.2f}, TP: {tp:.2f}\n"
            f"📊 *Recomendación*: Oportunidad inmediata si hay volumen.\n"
        )
        print("✅ Señal LONG detectada")
        send_telegram_message(message)

    elif prev['ema_13'] > prev['ema_55'] and last['ema_13'] < last['ema_55']:
        entry = last['close']
        sl = entry + last['atr']
        tp = entry - 2 * last['atr']
        message = (
            "📉 *Señal de VENTA (SHORT)*\n"
            f"🔹 Precio actual: {entry:.2f}\n"
            f"🔹 EMA 13 cruzó bajo EMA 55\n"
            f"🔹 SL: {sl:.2f}, TP: {tp:.2f}\n"
            f"📊 *Recomendación*: Momentum bajista confirmado.\n"
        )
        print("✅ Señal SHORT detectada")
        send_telegram_message(message)
    else:
        print("⏳ No hay señal en este momento")

# Bucle de ejecución continua
while True:
    try:
        check_signal()
        time.sleep(60)
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(60)
