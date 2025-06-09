import requests
import pandas as pd
import numpy as np
import datetime as dt
import time

class TradingBot:
    def __init__(self, telegram_token, chat_id):
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.last_signal = None
        self.last_check = None
        self.error_count = 0
        self.recent_signals = []

    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        try:
            requests.post(url, data=payload)
        except Exception as e:
            print(f"Error sending message to Telegram: {e}")

    def fetch_ohlcv_data(self):
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': '7',
            'interval': 'hourly'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()['prices']

        df = pd.DataFrame(data, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['Close'] = df['price']
        df.drop('price', axis=1, inplace=True)

        # Calcular EMAs y ATR
        df['EMA_13'] = df['Close'].ewm(span=13, adjust=False).mean()
        df['EMA_55'] = df['Close'].ewm(span=55, adjust=False).mean()
        df['High'] = df['Close'] * (1 + np.random.uniform(0.001, 0.01, len(df)))  # Mock
        df['Low'] = df['Close'] * (1 - np.random.uniform(0.001, 0.01, len(df)))  # Mock
        df['ATR'] = self.calculate_atr(df)
        return df

    def calculate_atr(self, df, period=14):
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        tr = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def get_current_price(self):
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'bitcoin',
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()['bitcoin']

    def get_recent_signals(self):
        return self.recent_signals[-10:]

    def check_signal(self):
        try:
            df = self.fetch_ohlcv_data()
            self.last_check = str(dt.datetime.now())
            latest = df.iloc[-1]
            previous = df.iloc[-2]

            signal = None
            if previous['EMA_13'] < previous['EMA_55'] and latest['EMA_13'] > latest['EMA_55']:
                signal = 'LONG'
            elif previous['EMA_13'] > previous['EMA_55'] and latest['EMA_13'] < latest['EMA_55']:
                signal = 'SHORT'

            if signal:
                entry_price = latest['Close']
                atr = latest['ATR']

                if signal == 'LONG':
                    sl = round(entry_price - 0.75 * atr, 2)
                    tp = round(entry_price + 2 * atr, 2)
                    msg = (
                        f"\U0001F4C8 *Se\u00f1al LONG Detectada*\n\n"
                        f"🟢 Precio de entrada: {entry_price:.2f} USD\n"
                        f"🔵 Take Profit (TP): {tp:.2f} USD\n"
                        f"🔴 Stop Loss (SL): {sl:.2f} USD"
                    )
                else:
                    sl = round(entry_price + 0.75 * atr, 2)
                    tp = round(entry_price - 2 * atr, 2)
                    msg = (
                        f"\U0001F4C9 *Se\u00f1al SHORT Detectada*\n\n"
                        f"🔴 Precio de entrada: {entry_price:.2f} USD\n"
                        f"🔵 Take Profit (TP): {tp:.2f} USD\n"
                        f"🟢 Stop Loss (SL): {sl:.2f} USD"
                    )

                self.send_telegram_message(msg)
                self.last_signal = signal
                self.recent_signals.append({
                    'time': str(dt.datetime.now()),
                    'signal': signal,
                    'entry': entry_price,
                    'tp': tp,
                    'sl': sl
                })

        except Exception as e:
            print(f"❌ Error in check_signal: {e}")
            raise
