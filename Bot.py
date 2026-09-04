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
    "GOLD": "GC=F"
}

TIMEFRAME_MAP = {
    "1m": ("1 Dəqiqə", "1m", "1d"),
    "5m": ("5 Dəqiqə", "5m", "1d"),
    "15m": ("15 Dəqiqə", "15m", "5d"),
    "30m": ("30 Dəqiqə", "30m", "5d"),
    "1h": ("1 Saat", "1h", "1mo"),
    "4h": ("4 Saat", "1h", "3mo")
}

user_data = {}

# --- CANLI QİYMƏTLƏRİ ÇƏKMƏK ---
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

# --- 6 İNDİKATOR HESABLANMASI ---
def calc_rsi(prices, period=14):
    if len(prices) < period + 1: return 50, 0
    gains = [max(prices[i] - prices[i-1], 0) for i in range(1, len(prices))]
    losses = [max(prices[i-1] - prices[i], 0) for i in range(1, len(prices))]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100, 1
    rsi = round(100 - (100 / (1 + (avg_gain / avg_loss))), 2)
    score = 1 if rsi < 35 else (-1 if rsi > 65 else 0)
    return rsi, score

def calc_stochastic(prices, period=14):
    if len(prices) < period: return 50, 0
    recent = prices[-period:]
    low_min, high_max = min(recent), max(recent)
    if high_max == low_min: return 50, 0
    stoch = round(((prices[-1] - low_min) / (high_max - low_min)) * 100, 2)
    score = 1 if stoch < 20 else (-1 if stoch > 80 else 0)
    return stoch, score

def calc_ema(prices, period):
    if len(prices) < period: return prices[-1]
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def analyze_ema(prices):
    if len(prices) < 50: return "Nötr", 0
    ema20, ema50 = calc_ema(prices, 20), calc_ema(prices, 50)
    if ema20 > ema50: return "Yuxarı 📈", 1
    elif ema20 < ema50: return "Aşağı 📉", -1
    return "Yatay ➖", 0

def calc_macd(prices):
    if len(prices) < 26: return "Nötr", 0
    macd_line = calc_ema(prices, 12) - calc_ema(prices, 26)
    return ("BULLISH 🟢", 1) if macd_line > 0 else ("BEARISH 🔴", -1)

def calc_bollinger(prices, period=20):
    if len(prices) < period: return "Zolaq İçi", 0
    recent = prices[-period:]
    sma = sum(recent) / period
    std_dev = (sum((x - sma) ** 2 for x in recent) / period) ** 0.5
    curr = prices[-1]
    if curr <= sma - (2 * std_dev): return "Alt Zolaq Qırılıb 🟢", 1
    elif curr >= sma + (2 * std_dev): return "Üst Zolaq Qırılıb 🔴", -1
    return "Kanal Daxili ⚪️", 0

def calc_momentum(prices):
    if len(prices) < 4: return "Sakit", 0
    diff = prices[-1] - prices[-4]
    if diff > 0: return "Yuxarı İmpuls 🟢", 1
    elif diff < 0: return "Aşağı İmpuls 🔴", -1
    return "Qərarsız ⚪️", 0

# --- SƏLİQƏLİ INLINE MENYULAR ---

def get_pair_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💶 EUR/USD", callback_data="pair_EUR/USD")
    btn2 = types.InlineKeyboardButton("💷 GBP/USD", callback_data="pair_GBP/USD")
    btn3 = types.InlineKeyboardButton("💴 USD/JPY", callback_data="pair_USD/JPY")
    btn4 = types.InlineKeyboardButton("🇦🇺 AUD/USD", callback_data="pair_AUD/USD")
    btn5 = types.InlineKeyboardButton("🇨🇦 USD/CAD", callback_data="pair_USD/CAD")
    btn6 = types.InlineKeyboardButton("🏆 GOLD (Qızıl)", callback_data="pair_GOLD")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

def get_time_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("⏱ 1 Dəqiqə", callback_data="tf_1m")
    btn2 = types.InlineKeyboardButton("⏱ 5 Dəqiqə", callback_data="tf_5m")
    btn3 = types.InlineKeyboardButton("⏱ 15 Dəqiqə", callback_data="tf_15m")
    btn4 = types.InlineKeyboardButton("⏱ 30 Dəqiqə", callback_data="tf_30m")
    btn5 = types.InlineKeyboardButton("⏱ 1 Saat", callback_data="tf_1h")
    btn6 = types.InlineKeyboardButton("⏱ 4 Saat", callback_data="tf_4h")
    btn_back = types.InlineKeyboardButton("⬅️ BAZAR MENYUSUNA QAYIT", callback_data="back_to_pairs")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    markup.add(btn_back)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Aşağıdakı klaviaturanı silmək üçün
    remove_markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id, 
        "🚀 **6-İndikatorlu Analiz Botuna Xoş Qəldiniz!**\n\nAnaliz etmək istədiyiniz **BAZARI** aşağıdakı menyudan seçin:", 
        parse_mode="Markdown", 
        reply_markup=get_pair_inline_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("pair_"):
        selected_pair = data.replace("pair_", "")
        if selected_pair == "GOLD": selected_pair = "GOLD"
        user_data[chat_id] = selected_pair
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"📌 Seçilmiş Aktiv: **{selected_pair}**\n\nİndi istədiyiniz **TAYMFREYMI** seçin:",
            parse_mode="Markdown",
            reply_markup=get_time_inline_keyboard()
        )

    elif data == "back_to_pairs":
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="📊 Analiz etmək istədiyiniz **BAZARI** seçin:",
            parse_mode="Markdown",
            reply_markup=get_pair_inline_keyboard()
        )

    elif data.startswith("tf_"):
        tf_key = data.replace("tf_", "")
        tf_name, interval, range_str = TIMEFRAME_MAP[tf_key]
        selected_pair = user_data.get(chat_id, "EUR/USD")
        yahoo_symbol = SYMBOLS.get(selected_pair, "EURUSD=X")

        bot.answer_callback_query(call.id, text="Canlı bazar analiz olunur...")

        prices = get_market_prices(yahoo_symbol, interval=interval, range_str=range_str)

        if prices and len(prices) > 30:
            curr_p = prices[-1]
            rsi_val, rsi_score = calc_rsi(prices)
            stoch_val, stoch_score = calc_stochastic(prices)
            ema_str, ema_score = analyze_ema(prices)
            macd_str, macd_score = calc_macd(prices)
            boll_str, boll_score = calc_bollinger(prices)
            mom_str, mom_score = calc_momentum(prices)

            total_score = rsi_score + stoch_score + ema_score + macd_score + boll_score + mom_score

            if total_score >= 4:
                final_decision = "🟢 **GÜCLÜ CALL (YUXARI) ⬆️**\n*İndikatorların çoxu artım göstərir.*"
            elif total_score <= -4:
                final_decision = "🔴 **GÜCLÜ PUT (AŞAĞI) ⬇️**\n*İndikatorların çoxu düşüş göstərir.*"
            elif total_score in [2, 3]:
                final_decision = "🟢 **ZƏİF CALL (YUXARI) ↗️**\n*Risklidir, ehtiyatlı olun.*"
            elif total_score in [-2, -3]:
                final_decision = "🔴 **ZƏİF PUT (AŞAĞI) ↘️**\n*Risklidir, ehtiyatlı olun.*"
            else:
                final_decision = "⚠️ **NO TRADE / NÖTR (GÖZLƏYİN) 🛑**\n*Bazar qərarsızdır və ya aldatmaca var. Əməliyyat açmayın!*"

            msg = (
                f"📊 **CANLI BAZAR ANALİZİ**\n"
                f"────────────────────────\n"
                f"💱 **Aktiv:** `{selected_pair}`\n"
                f"⏱ **Taymfreym:** `{tf_name}`\n"
                f"💲 **Cari Qiymət:** `{curr_p:.5f}`\n"
                f"────────────────────────\n"
                f"1️⃣ **RSI (14):** `{rsi_val}`\n"
                f"2️⃣ **Stochastic:** `{stoch_val}%`\n"
                f"3️⃣ **EMA Trend:** `{ema_str}`\n"
                f"4️⃣ **MACD:** `{macd_str}`\n"
                f"5️⃣ **Bollinger:** `{boll_str}`\n"
                f"6️⃣ **Momentum:** `{mom_str}`\n"
                f"────────────────────────\n"
                f"📈 **Səsvermə Nəticəsi:** `{total_score} / +6`\n"
                f"🎯 **YEKUN QƏRAR:**\n{final_decision}"
            )
            
            # Nəticə gələndən sonra yenidən menyunu altında saxlayır
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=get_pair_inline_keyboard())
        else:
            bot.send_message(chat_id, "❌ BAZAR BAĞLIDIR və ya qiymət alınamadı.", reply_markup=get_pair_inline_keyboard())

print("Bot işə düşdü...")
bot.infinity_polling()
