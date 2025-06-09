import requests
import time
from datetime import datetime

class TradingBot:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_signal = None
        self.error_count = 0

    def send_telegram_message(self, message):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Error enviando mensaje a Telegram: {e}")

    def check_signal_loop(self):
        while True:
            try:
                self.check_signal()
            except Exception as e:
                print(f"❌ Error en check_signal: {e}")
                self.error_count += 1
            time.sleep(60)  # cada minuto

    def check_signal(self):
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "hourly"
        }

        response = requests.get(url, params=params)
        data = response.json()
        prices = data["prices"]

        if len(prices) < 55:
            return  # no hay datos suficientes

        close_prices = [p[1] for p in prices]
        ema_13 = self.ema(close_prices, 13)
        ema_55 = self.ema(close_prices, 55)

        if ema_13[-1] > ema_55[-1] and ema_13[-2] <= ema_55[-2]:
            signal = "LONG"
        elif ema_13[-1] < ema_55[-1] and ema_13[-2] >= ema_55[-2]:
            signal = "SHORT"
        else:
            return

        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        msg = f"{'📈' if signal == 'LONG' else '📉'} *Señal {signal} Detectada*\n\nFecha UTC: `{timestamp}`\nPrecio: `${close_prices[-1]:.2f}`"
        self.last_signal = msg
        self.send_telegram_message(msg)

    def ema(self, data, period):
        ema_values = []
        k = 2 / (period + 1)
        ema_prev = sum(data[:period]) / period
        ema_values.extend([None] * (period - 1))
        ema_values.append(ema_prev)
        for price in data[period:]:
            ema = price * k + ema_prev * (1 - k)
            ema_values.append(ema)
            ema_prev = ema
        return ema_values
