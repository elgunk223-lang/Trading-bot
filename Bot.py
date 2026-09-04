# -*- coding: utf-8 -*-
import os
import json
import time
import urllib.request
import threading
from flask import Flask
import telebot
from telebot import types

# --- RENDER ÜÇÜN FLASK SERVERİ ---
app = Flask('')

@app.route('/')
def home():
    return "Bot status: Active"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- BOT NİZAMLAMALARI ---
TELEGRAM_TOKEN = "8911527218:AAE1IQ-lNNk7tw3m03OJgIFM5OSvkjncxaI"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYMBOLS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "GOLD (Qızıl)": "GC=F"
}

# Taymfreymlərə uyğun Yahoo Finance intervalları
TIMEFRAME_MAP = {
    "1 Dəqiqə": ("1m", "1d"),
    "5 Dəqiqə": ("5m", "1d"),
    "15 Dəqiqə": ("15m", "5d"),
    "30 Dəqiqə": ("30m", "5d"),
    "1 Saat": ("1h", "1mo"),
    "4 Saat": ("1h", "3mo") # Yahoo API-də 4h üçün 1h istifadə olunub birləşdirilir
}

user_data = {}

def get_market_prices(symbol, interval="1m", range_str="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_str}"
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
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(change if change > 0 else 0)
        losses.append(abs(change) if change < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calculate_ema(prices, period=14):
    if len(prices) < period:
        return prices[-1] if prices else 0
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

# --- TELEGRAM BOT DÜYMƏLƏRİ VƏ ƏMƏLİYYATLAR ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    show_pair_menu(message.chat.id)

def show_pair_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton("1. EUR/USD"),
        types.KeyboardButton("2. GBP/USD"),
        types.KeyboardButton("3. USD/JPY"),
        types.KeyboardButton("4. AUD/USD"),
        types.KeyboardButton("5. USD/CAD"),
        types.KeyboardButton("6. GOLD (Qızıl)")
    ]
    markup.add(*buttons)
    bot.send_message(chat_id, "🚀 **Manual Analiz Botu Aktivdir!**\n\n📊 Analiz etmək istədiyiniz BAZARI seçin:", parse_mode="Markdown", reply_markup=markup)

def show_time_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        types.KeyboardButton("1 Dəqiqə"),
        types.KeyboardButton("5 Dəqiqə"),
        types.KeyboardButton("15 Dəqiqə"),
        types.KeyboardButton("30 Dəqiqə"),
        types.KeyboardButton("1 Saat"),
        types.KeyboardButton("4 Saat"),
        types.KeyboardButton("⬅️ Geri (Bazar Seçimi)")
    ]
    markup.add(*buttons)
    bot.send_message(chat_id, "⏱ **Taymfreym seçin:**", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    text = message.text
    chat_id = message.chat.id

    if "EUR/USD" in text:
        user_data[chat_id] = "EUR/USD"
        show_time_menu(chat_id)
    elif "GBP/USD" in text:
        user_data[chat_id] = "GBP/USD"
        show_time_menu(chat_id)
    elif "USD/JPY" in text:
        user_data[chat_id] = "USD/JPY"
        show_time_menu(chat_id)
    elif "AUD/USD" in text:
        user_data[chat_id] = "AUD/USD"
        show_time_menu(chat_id)
    elif "USD/CAD" in text:
        user_data[chat_id] = "USD/CAD"
        show_time_menu(chat_id)
    elif "GOLD" in text:
        user_data[chat_id] = "GOLD (Qızıl)"
        show_time_menu(chat_id)
    elif text == "⬅️ Geri (Bazar Seçimi)":
        show_pair_menu(chat_id)
    elif text in TIMEFRAME_MAP:
        selected_pair = user_data.get(chat_id, "EUR/USD")
        yahoo_symbol = SYMBOLS.get(selected_pair, "EURUSD=X")
        interval, range_str = TIMEFRAME_MAP[text]
        
        bot.send_message(chat_id, f"⏳ **{selected_pair} ({text}) canlı bazarı analiz olunur...**", parse_mode="Markdown")
        
        prices = get_market_prices(yahoo_symbol, interval=interval, range_str=range_str)
        
        if prices and len(prices) > 20:
            curr_p = prices[-1]
            rsi = calculate_rsi(prices)
            ema = calculate_ema(prices)
            
            # Trend və İndikator Təhlili
            trend = "YUXARI 🟢" if curr_p > ema else "AŞAĞI 🔴"
            
            # Siqnal Mexanizmi
            if rsi < 35 and curr_p > ema:
                signal_text = "🟢 **GÜCLÜ CALL (YUXARI)** ⬆️"
            elif rsi < 40:
                signal_text = "🟢 **CALL (YUXARI)** ⬆️"
            elif rsi > 65 and curr_p < ema:
                signal_text = "🔴 **GÜCLÜ PUT (AŞAĞI)** ⬇️"
            elif rsi > 60:
                signal_text = "🔴 **PUT (AŞAĞI)** ⬇️"
            else:
                signal_text = "⚪️ **NÖTR (Bazar Stabil - Gözləyin)**"
            
            msg = (
                f"📈 **CANLI BAZAR ANALİZİ**\n"
                f"─────────────────\n"
                f"💱 **Aktiv:** {selected_pair}\n"
                f"⏱ **Taymfreym:** {text}\n"
                f"💲 **Cari Qiymət:** `{curr_p:.5f}`\n"
                f"📊 **RSI (14):** `{rsi}`\n"
                f"📉 **Trend (EMA 14):** {trend}\n"
                f"─────────────────\n"
                f"🎯 **TÖVSİYƏ:** {signal_text}"
            )
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ BAZAR BAĞLIDIR və ya məlumat çəkilə bilmədi. Bir az sonra yenidən cəhd edin.")

print("Bot işə düşdü...")
bot.infinity_polling()
