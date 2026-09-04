# -*- coding: utf-8 -*-
import json
import time
import urllib.request
import os
import threading
from flask import Flask

# --- RENDER ÜÇÜN FLASK SERVERİ ---
app = Flask('')

@app.route('/')
def home():
    return "Bot status: Active"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Flask serverini arxa fonda başladırıq
threading.Thread(target=run_flask, daemon=True).start()

# --- SİZİN BOT KODUNUZ ---
TELEGRAM_TOKEN = "8911527218:AAE1IQ-lNNk7tw3m03OJgIFM5OSvkjncxaI"
CHAT_ID = "7508094911"
SYMBOL = "EURUSD=X"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"Telegram xətası: {e}")
        return False

def get_market_prices(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            prices = data['chart']['result'][0]['indicators']['quote'][0]['close']
            return [p for p in prices if p is not None]
    except Exception as e:
        print(f"Qiymət xətası: {e}")
        return []

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(change if change > 0 else 0)
        losses.append(abs(change) if change < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

print("Bot işə düşdü...")
send_telegram("🚀 **Pocket Option Botu Aktivdir!** (Pulsuz Versiya)")

last_signal = 0
while True:
    prices = get_market_prices(SYMBOL)
    if prices and len(prices) > 15:
        curr_p = prices[-1]
        rsi = calculate_rsi(prices)
        if rsi:
            print(f"Qiymət: {curr_p:.5f} | RSI: {rsi:.2f}")
            if time.time() - last_signal > 60:
                if rsi < 30:
                    send_telegram(f"🟢 **CALL (YUXARI)**\nAktiv: EUR/USD\nRSI: {rsi:.2f}\nQiymət: {curr_p:.5f}")
                    last_signal = time.time()
                elif rsi > 70:
                    send_telegram(f"🔴 **PUT (AŞAĞI)**\nAktiv: EUR/USD\nRSI: {rsi:.2f}\nQiymət: {curr_p:.5f}")
                    last_signal = time.time()
    time.sleep(10)
