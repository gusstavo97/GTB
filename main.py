from flask import Flask, render_template, jsonify, request
import threading
import time
import os
from bot import TradingBot

app = Flask(__name__)

# Global bot instance
trading_bot = None
bot_thread = None
bot_running = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    global bot_running, trading_bot
    status = {
        'running': bot_running,
        'last_check': trading_bot.last_check if trading_bot else None,
        'last_signal': trading_bot.last_signal if trading_bot else None,
        'error_count': trading_bot.error_count if trading_bot else 0
    }
    return jsonify(status)

@app.route('/api/current_price')
def get_current_price():
    global trading_bot
    if trading_bot:
        try:
            price_data = trading_bot.get_current_price()
            return jsonify(price_data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Bot not initialized'}), 400

@app.route('/api/signals')
def get_signals():
    global trading_bot
    if trading_bot:
        return jsonify({'signals': trading_bot.get_recent_signals()})
    return jsonify({'signals': []})

@app.route('/api/start_bot', methods=['POST'])
def start_bot():
    send_telegram_message("🟢 Bot iniciado correctamente. Probando conexión con Telegram.")
    global trading_bot, bot_thread, bot_running
    
    if bot_running:
        return jsonify({'error': 'Bot is already running'}), 400
    
    try:
        # Get credentials from environment variables
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '7274514132:AAFdt_Vr48MyKmJigy0WSNWrkgy6LWB1LI4')
        chat_id = int(os.getenv('TELEGRAM_CHAT_ID', '5253696321'))
        
        trading_bot = TradingBot(bot_token, chat_id)
        bot_running = True
        
        # Start bot in separate thread
        bot_thread = threading.Thread(target=run_bot_loop, daemon=True)
        bot_thread.start()
        
        return jsonify({'message': 'Bot started successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop_bot', methods=['POST'])
def stop_bot():
    global bot_running
    bot_running = False
    return jsonify({'message': 'Bot stopped'})

def run_bot_loop():
    global bot_running, trading_bot
    while bot_running:
        try:
            trading_bot.check_signal()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Bot error: {e}")
            if trading_bot:
                trading_bot.error_count += 1
            time.sleep(60)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
