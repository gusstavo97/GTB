import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime

class TradingBot:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_key = os.getenv("COINGECKO_API_KEY")
        self.base_url = "https://api.coingecko.com/api/v3"
        self.last_signal = None
        self.last_check = None
        self.error_count = 0
        self.signals = []

    def send_telegram_message(self, text):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"Error sending message to Telegram: {e}")

    def get_current_price(self):
        url = f"{self.base_url}/simple/price"
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        headers = {'x-cg-demo-api-key': self.api_key} if self.api_key else {}
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting current price: {e}")
            raise

    def get_price_history(self):
        url = f"{self.base_url}/coins/bitcoin/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': '7',
            'interval': 'hourly'
        }
        headers = {'x-cg-demo-api-key': self.api_key} if self.api_key else {}
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            prices = response.json().get("prices", [])
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            return df[['price']]
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            raise

    def calculate_atr(self, df, period=14):
        df['high'] = df['price'] * 1.01
        df['low'] = df['price'] * 0.99
        df['close'] = df['price']

        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def calculate_sl_tp(self, current_price, signal, atr_value):
        if signal == 'LONG':
            sl = current_price - atr_value
            tp = current_price + 2 * atr_value
        else:
            sl = current_price + atr_value
            tp = current_price - 2 * atr_value
        return sl, tp

    def check_signal(self):
        try:
            df = self.get_price_history()
            if len(df) < 55:
                print("Not enough data to calculate EMAs")
                return

            df['ema_13'] = df['price'].ewm(span=13, adjust=False).mean()
            df['ema_55'] = df['price'].ewm(span=55, adjust=False).mean()
            df['atr'] = self.calculate_atr(df)

            last = df.iloc[-1]
            prev = df.iloc[-2]
            current_price = last['price']
            atr_value = last['atr']

            signal = None
            if prev['ema_13'] < prev['ema_55'] and last['ema_13'] > last['ema_55']:
                signal = 'LONG'
            elif prev['ema_13'] > prev['ema_55'] and last['ema_13'] < last['ema_55']:
                signal = 'SHORT'

            if signal:
                sl, tp = self.calculate_sl_tp(current_price, signal, atr_value)
                msg = f"{'\ud83d\udcc8' if signal == 'LONG' else '\ud83d\udcc9'} *Se\u00f1al {signal} Detectada*\n\n"
                msg += f"Precio actual: ${current_price:.2f}\n"
                msg += f"EMA 13: ${last['ema_13']:.2f} | EMA 55: ${last['ema_55']:.2f}\n"
                msg += f"ATR: ${atr_value:.2f}\n\n"
                msg += f"\ud83c\udfaf *Gesti\u00f3n de Riesgo:*\n"
                msg += f"Stop Loss: ${sl:.2f}\n"
                msg += f"Take Profit: ${tp:.2f}\n"
                msg += f"R/R Ratio: 1:2\n"

                self.send_telegram_message(msg)
                self.last_signal = f"{signal} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.signals.append(self.last_signal)

            self.last_check = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"\u274c Error in check_signal: {e}")
            raise

    def get_recent_signals(self, limit=10):
        return self.signals[-limit:]
