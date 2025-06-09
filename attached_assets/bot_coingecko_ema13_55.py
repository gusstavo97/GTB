
import time
import requests
import pandas as pd

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

def get_btc_price():
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': 'bitcoin',
        'vs_currencies': 'usd'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()['bitcoin']['usd']
    else:
        print("❌ Error al obtener el precio desde CoinGecko")
        return None

def get_price_history():
    url = 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart'
    params = {
        'vs_currency': 'usd',
        'days': '1',
        'interval': 'minute'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        return df
    else:
        print("❌ Error al obtener datos históricos desde CoinGecko")
        return pd.DataFrame()

def check_signal(df):
    df['ema_13'] = df['price'].ewm(span=13, adjust=False).mean()
    df['ema_55'] = df['price'].ewm(span=55, adjust=False).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    print(f"[{pd.Timestamp.now()}] Revisando señal...")

    if prev['ema_13'] < prev['ema_55'] and last['ema_13'] > last['ema_55']:
        msg = f"📈 *Señal de COMPRA (LONG)*\nPrecio actual: ${last['price']:.2f}\nCruce EMA 13 sobre EMA 55"
        print("✅ Señal LONG detectada")
        send_telegram_message(msg)

    elif prev['ema_13'] > prev['ema_55'] and last['ema_13'] < last['ema_55']:
        msg = f"📉 *Señal de VENTA (SHORT)*\nPrecio actual: ${last['price']:.2f}\nCruce EMA 13 bajo EMA 55"
        print("✅ Señal SHORT detectada")
        send_telegram_message(msg)
    else:
        print("⏳ No hay señal en este momento")

# Bucle principal
while True:
    try:
        df = get_price_history()
        if not df.empty:
            check_signal(df)
        time.sleep(60)
    except Exception as e:
        print("❌ Error general:", e)
        time.sleep(60)
