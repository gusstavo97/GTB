import pandas as pd
import time
import requests
from ta.volatility import AverageTrueRange
from ta.trend import EMAIndicator
from datetime import datetime, timedelta

class TradingBot:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.last_check = None
        self.last_signal = None
        self.error_count = 0
        self.recent_signals = []
        # Use CoinGecko API (free, global, no restrictions)
        self.base_url = "https://api.coingecko.com/api/v3"

    def send_telegram_message(self, text):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, data=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False

    def fetch_ohlcv(self):
        """Fetch OHLCV data from CoinGecko"""
        try:
            # Get historical data for the last 7 days with hourly intervals
            url = f"{self.base_url}/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': '7',
                'interval': 'hourly'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Convert to OHLCV format
            prices = data['prices']
            volumes = data['total_volumes']
            
            # Create DataFrame with price data
            df_data = []
            for i in range(len(prices)):
                timestamp = prices[i][0]
                price = prices[i][1]
                volume = volumes[i][1] if i < len(volumes) else 0
                
                df_data.append({
                    'timestamp': timestamp,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                })
            
            df = pd.DataFrame(df_data)
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            # Keep last 100 records
            return df.tail(100)
            
        except Exception as e:
            print(f"Error fetching OHLCV data: {e}")
            raise

    def get_current_price(self):
        """Get current BTC/USD price and basic info"""
        try:
            # Get current price and market data
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            price_data = response.json()
            
            bitcoin_data = price_data['bitcoin']
            current_price = bitcoin_data['usd']
            change_24h = bitcoin_data.get('usd_24h_change', 0)
            volume_24h = bitcoin_data.get('usd_24h_vol', 0)
            
            # Get historical data for indicators
            df = self.fetch_ohlcv()
            
            # Calculate indicators
            close_series = df['close'].astype(float)
            high_series = df['high'].astype(float)
            low_series = df['low'].astype(float)
            
            df['ema_13'] = EMAIndicator(close=close_series, window=13).ema_indicator()
            df['ema_55'] = EMAIndicator(close=close_series, window=55).ema_indicator()
            df['atr'] = AverageTrueRange(high=high_series, low=low_series, close=close_series, window=14).average_true_range()
            
            last = df.iloc[-1]
            
            return {
                'price': current_price,
                'change_24h': change_24h,
                'volume_24h': volume_24h,
                'ema_13': float(last['ema_13']),
                'ema_55': float(last['ema_55']),
                'atr': float(last['atr']),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting current price: {e}")
            raise

    def check_signal(self):
        """Check for trading signals"""
        try:
            df = self.fetch_ohlcv()
            
            # Calculate indicators
            close_series = df['close'].astype(float)
            high_series = df['high'].astype(float)
            low_series = df['low'].astype(float)
            
            df['ema_13'] = EMAIndicator(close=close_series, window=13).ema_indicator()
            df['ema_55'] = EMAIndicator(close=close_series, window=55).ema_indicator()
            df['atr'] = AverageTrueRange(high=high_series, low=low_series, close=close_series, window=14).average_true_range()

            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            self.last_check = datetime.now().isoformat()

            print(f"[{pd.Timestamp.now()}] Revisando señal...")

            signal_detected = False

            # Check for LONG signal (EMA 13 crosses above EMA 55)
            if prev['ema_13'] < prev['ema_55'] and last['ema_13'] > last['ema_55']:
                entry = last['close']
                sl = entry - last['atr']
                tp = entry + 2 * last['atr']
                
                signal_data = {
                    'type': 'LONG',
                    'timestamp': datetime.now().isoformat(),
                    'entry': float(entry),
                    'stop_loss': float(sl),
                    'take_profit': float(tp),
                    'atr': float(last['atr'])
                }
                
                message = (
                    "📈 *Señal de COMPRA (LONG)*\n"
                    f"🔹 Precio actual: {entry:.2f}\n"
                    f"🔹 EMA 13 cruzó sobre EMA 55\n"
                    f"🔹 SL: {sl:.2f}, TP: {tp:.2f}\n"
                    f"📊 *Recomendación*: Oportunidad inmediata si hay volumen.\n"
                )
                
                print("✅ Señal LONG detectada")
                self.send_telegram_message(message)
                self.last_signal = signal_data
                self.recent_signals.append(signal_data)
                signal_detected = True

            # Check for SHORT signal (EMA 13 crosses below EMA 55)
            elif prev['ema_13'] > prev['ema_55'] and last['ema_13'] < last['ema_55']:
                entry = last['close']
                sl = entry + last['atr']
                tp = entry - 2 * last['atr']
                
                signal_data = {
                    'type': 'SHORT',
                    'timestamp': datetime.now().isoformat(),
                    'entry': float(entry),
                    'stop_loss': float(sl),
                    'take_profit': float(tp),
                    'atr': float(last['atr'])
                }
                
                message = (
                    "📉 *Señal de VENTA (SHORT)*\n"
                    f"🔹 Precio actual: {entry:.2f}\n"
                    f"🔹 EMA 13 cruzó bajo EMA 55\n"
                    f"🔹 SL: {sl:.2f}, TP: {tp:.2f}\n"
                    f"📊 *Recomendación*: Momentum bajista confirmado.\n"
                )
                
                print("✅ Señal SHORT detectada")
                self.send_telegram_message(message)
                self.last_signal = signal_data
                self.recent_signals.append(signal_data)
                signal_detected = True

            if not signal_detected:
                print("⏳ No hay señal en este momento")

            # Keep only last 10 signals
            if len(self.recent_signals) > 10:
                self.recent_signals = self.recent_signals[-10:]

        except Exception as e:
            print(f"❌ Error in check_signal: {e}")
            self.error_count += 1
            raise

    def get_recent_signals(self):
        """Get list of recent signals"""
        return list(reversed(self.recent_signals))  # Most recent first
