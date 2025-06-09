from flask import Flask, jsonify
from bot import TradingBot
import threading
import os

app = Flask(__name__)

# Iniciar bot automáticamente al arrancar
bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")

trading_bot = TradingBot(bot_token, chat_id)

def run_bot():
    try:
        trading_bot.send_telegram_message("🤖 Bot EMA 13/55 iniciado en Render.")
        trading_bot.check_signal_loop()
    except Exception as e:
        print(f"Bot failed: {e}")

threading.Thread(target=run_bot, daemon=True).start()

@app.route('/')
def home():
    return "Bot de Trading EMA 13/55 en funcionamiento. Usa la API para interactuar."

@app.route('/api/status')
def status():
    return jsonify({"status": "ok", "message": "Bot corriendo", "last_signal": trading_bot.last_signal})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
