import time
import requests
import pandas as pd
import os
import numpy as np

# Configuration
bot_token = "7274514132:AAFdt_Vr48MyKmJigy0WSNWrkgy6LWB1LI4"
chat_id = 5253696321
coingecko_api_key = os.getenv('COINGECKO_API_KEY')
if coingecko_api_key:
    coingecko_api_key = coingecko_api_key.strip()

def send_telegram_message(text):
    """Send message to Telegram bot"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ Mensaje enviado a Telegram")
        else:
            print(f"❌ Error enviando mensaje a Telegram: {response.status_code}")
    except Exception as e:
        print(f"❌ Error enviando mensaje a Telegram: {e}")

def get_btc_price():
    """Get current BTC price from CoinGecko"""
    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': 'bitcoin',
        'vs_currencies': 'usd'
    }
    
    headers = {}
    if coingecko_api_key:
        headers['x-cg-demo-api-key'] = coingecko_api_key
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            return response.json()['bitcoin']['usd']
        else:
            print(f"❌ Error al obtener el precio desde CoinGecko: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error al obtener el precio: {e}")
        return None

def get_price_history():
    """Get Bitcoin price history with OHLC data from CoinGecko"""
    url = 'https://api.coingecko.com/api/v3/coins/bitcoin/ohlc'
    params = {
        'vs_currency': 'usd',
        'days': '30'
    }
    
    headers = {}
    if coingecko_api_key:
        headers['x-cg-demo-api-key'] = coingecko_api_key
        print(f"🔑 Usando API key (primeros 10 chars): {coingecko_api_key[:10]}...")
    else:
        print("⚠️ No se encontró API key")
    
    try:
        response = requests.get(url, params=params, headers=headers)
        print(f"📡 Respuesta del servidor: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # OHLC data format: [timestamp, open, high, low, close]
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            df['price'] = df['close']  # Use close price for EMA calculations
            print(f"✅ Obtenidos {len(df)} puntos de datos OHLC")
            return df
        else:
            print(f"❌ Error al obtener datos históricos desde CoinGecko: {response.status_code}")
            print(f"Respuesta del servidor: {response.text[:200]}")
            if response.status_code == 401:
                print("💡 Necesitas una API key de CoinGecko para acceso completo")
            elif response.status_code == 429:
                print("💡 Límite de solicitudes excedido. Considera usar una API key de CoinGecko")
            return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error al obtener datos históricos: {e}")
        return pd.DataFrame()

def calculate_atr(df, period=14):
    """Calculate Average True Range (ATR)"""
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(period).mean()
    return atr

def calculate_sl_tp(current_price, signal, atr_value):
    """Calculate Stop Loss and Take Profit based on signal type and ATR"""
    if signal == 'LONG':
        sl = current_price - atr_value
        tp = current_price + 2 * atr_value
    elif signal == 'SHORT':
        sl = current_price + atr_value
        tp = current_price - 2 * atr_value
    else:
        sl = tp = None
    return sl, tp

def check_signal(df):
    """Check for EMA crossover signals with ATR-based SL/TP"""
    if len(df) < 55:
        print("⚠️ No hay suficientes datos para calcular EMAs")
        return
    
    # Calculate EMAs and ATR
    df['ema_13'] = df['price'].ewm(span=13, adjust=False).mean()
    df['ema_55'] = df['price'].ewm(span=55, adjust=False).mean()
    df['atr'] = calculate_atr(df)

    # Get last two data points
    last = df.iloc[-1]
    prev = df.iloc[-2]
    current_price = last['price']
    atr_value = last['atr']

    print(f"[{pd.Timestamp.now()}] Revisando señal...")
    print(f"Precio actual: ${current_price:.2f}")
    print(f"EMA 13: ${last['ema_13']:.2f} | EMA 55: ${last['ema_55']:.2f}")
    print(f"ATR: ${atr_value:.2f}")

    signal = None

    # Check for bullish crossover (EMA 13 crosses above EMA 55)
    if prev['ema_13'] < prev['ema_55'] and last['ema_13'] > last['ema_55']:
        signal = "LONG"
        sl, tp = calculate_sl_tp(current_price, signal, atr_value)
        
        msg = f"📈 *Señal de COMPRA (LONG)*\n\n"
        msg += f"Precio actual: ${current_price:.2f}\n"
        msg += f"EMA 13: ${last['ema_13']:.2f}\n"
        msg += f"EMA 55: ${last['ema_55']:.2f}\n"
        msg += f"ATR: ${atr_value:.2f}\n\n"
        msg += f"🎯 *Gestión de Riesgo:*\n"
        msg += f"Stop Loss: ${sl:.2f}\n"
        msg += f"Take Profit: ${tp:.2f}\n"
        msg += f"R/R Ratio: 1:2\n\n"
        msg += f"🔥 Cruce EMA 13 sobre EMA 55"
        
        print("✅ Señal LONG detectada")
        send_telegram_message(msg)

    # Check for bearish crossover (EMA 13 crosses below EMA 55)
    elif prev['ema_13'] > prev['ema_55'] and last['ema_13'] < last['ema_55']:
        signal = "SHORT"
        sl, tp = calculate_sl_tp(current_price, signal, atr_value)
        
        msg = f"📉 *Señal de VENTA (SHORT)*\n\n"
        msg += f"Precio actual: ${current_price:.2f}\n"
        msg += f"EMA 13: ${last['ema_13']:.2f}\n"
        msg += f"EMA 55: ${last['ema_55']:.2f}\n"
        msg += f"ATR: ${atr_value:.2f}\n\n"
        msg += f"🎯 *Gestión de Riesgo:*\n"
        msg += f"Stop Loss: ${sl:.2f}\n"
        msg += f"Take Profit: ${tp:.2f}\n"
        msg += f"R/R Ratio: 1:2\n\n"
        msg += f"🔥 Cruce EMA 13 bajo EMA 55"
        
        print("✅ Señal SHORT detectada")
        send_telegram_message(msg)
    else:
        print("⏳ No hay señal en este momento")

    return signal

def main():
    """Main trading bot loop"""
    print("🚀 Iniciando Bot de Trading EMA 13/55")
    print("📊 Monitoreando Bitcoin (BTC/USD)")
    print("⏰ Revisando cada 60 segundos...")
    
    if not coingecko_api_key:
        print("⚠️ No se encontró API key de CoinGecko. Usando acceso limitado.")
        print("💡 Para acceso completo, configura COINGECKO_API_KEY")
    
    # Send startup message
    startup_msg = "🤖 *Bot de Trading Iniciado*\n\nMonitoreando BTC/USD\nEstrategia: EMA 13/55 Crossover\nIntervalo: 1 minuto"
    send_telegram_message(startup_msg)
    
    # Main loop
    while True:
        try:
            print("\n" + "="*50)
            df = get_price_history()
            if not df.empty:
                signal = check_signal(df)
                if signal:
                    print(f"🎯 Señal {signal} procesada")
            else:
                print("❌ No se pudieron obtener datos de precio")
            
            print("😴 Esperando 60 segundos...")
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n🛑 Bot detenido por el usuario")
            stop_msg = "🛑 *Bot de Trading Detenido*\n\nMonitoreo pausado por el usuario"
            send_telegram_message(stop_msg)
            break
        except Exception as e:
            print(f"❌ Error general: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()