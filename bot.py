import time
import requests
import pandas as pd
import os
import numpy as np

class TradingBot:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.coingecko_api_key = os.getenv('COINGECKO_API_KEY')
        if self.coingecko_api_key:
            self.coingecko_api_key = self.coingecko_api_key.strip()

        self.last_check = None
        self.last_signal = None
        self.error_count = 0
        self.recent_signals = []

    def send_telegram_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, data=payload)
            if response.status_code == 200:
                print("✅ Mensaje enviado a Telegram")
            else:
                print(f"❌ Error enviando mensaje a Telegram: {response.status_code}")
                print(f"➡️ Respuesta: {response.text}")
                if response.status_code == 403:
                    print("🚫 El bot no tiene permiso para enviarte mensajes. ¿Le diste /start en Telegram?")
                if response.status_code == 400:
                    print("📛 Verifica que el chat_id esté bien escrito.")
        except Exception as e:
            print(f"❌ Excepción enviando mensaje a Telegram: {e}")

    def get_price_history(self):
        url = 'https://api.coingecko.com/api/v3/coins/bitcoin/ohlc'
        params = {'vs_currency': 'usd', 'days': '30'}
        headers = {}
        if self.coingecko_api_key:
            headers['x-cg-demo-api-key'] = self.coingecko_api_key

        try:
            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
                df['price'] = df['close']
                return df
            else:
                raise Exception(f"Error fetching OHLCV data: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            return pd.DataFrame()

    def get_current_price(self):
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        headers = {}
        if self.coingecko_api_key:
            headers['x-cg-demo-api-key'] = self.coingecko_api_key

        try:
            response = requests.get(url, params=params, headers=headers)
            if response.status_code == 200:
                return response.json()['bitcoin']
            else:
                raise Exception(f"Error getting current price: {response.status_code} {response.text}")
        except Exception as e:
            print(f"Error getting current price: {e}")
            raise

    def calculate_atr(self, df, period=14):
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        return atr

    def calculate_sl_tp(self, price, signal, atr):
        if signal == 'LONG':
            return price - atr, price + 2 * atr
        elif signal == 'SHORT':
            return price + atr, price - 2 * atr
        return None, None

    def check_signal(self):
        df = self.get_price_history()
        if df.empty or len(df) < 55:
            print("❌ No hay suficientes datos para calcular señales")
            return

        df['ema_13'] = df['price'].ewm(span=13, adjust=False).mean()
        df['ema_55'] = df['price'].ewm(span=55, adjust=False).mean()
        df['atr'] = self.calculate_atr(df)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        price = last['price']
        atr = last['atr']

        self.last_check = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        signal = None

        if prev['ema_13'] < prev['ema_55'] and last['ema_13'] > last['ema_55']:
            signal = "LONG"
        elif prev['ema_13'] > prev['ema_55'] and last['ema_13'] < last['ema_55']:
            signal = "SHORT"

        if signal:
            sl, tp = self.calculate_sl_tp(price, signal, atr)
            msg = f"{'📈' if signal == 'LONG' else '📉'} *Señal {signal} Detectada*
"
            msg += f"\nPrecio: ${price:.2f}\nEMA13: ${last['ema_13']:.2f} | EMA55: ${last['ema_55']:.2f}\n"
            msg += f"ATR: ${atr:.2f}\nSL: ${sl:.2f} | TP: ${tp:.2f} (R:R 1:2)"
            self.send_telegram_message(msg)
            self.last_signal = signal
            self.recent_signals.append({'timestamp': self.last_check, 'signal': signal, 'price': price})
        else:
            print("⏳ No hay señal en este momento")

    def get_recent_signals(self):
        return self.recent_signals[-10:]
