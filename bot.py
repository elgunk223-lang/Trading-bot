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
TELEGRAM_TOKEN = "8906009577:AAHuAnl7ze8y2DH2KFVQLXMj7o0ZQCm8fC4"
bot = telebot.TeleBot(TELEGRAM_TOKEN)

SYMBOLS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "EUR/GBP": "EURGBP=X",
    "GOLD (Qızıl)": "GC=F",
    "BITCOIN": "BTC-USD"
}

TIMEFRAME_MAP = {
    "1m": ("1 Dəqiqə", "1m", "1d"),
    "5m": ("5 Dəqiqə", "5m", "1d"),
    "15m": ("15 Dəqiqə", "15m", "5d"),
    "30m": ("30 Dəqiqə", "30m", "5d"),
    "1h": ("1 Saat", "1h", "1mo")
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

# --- 4 ƏSAS İNDİKATOR HESABLANMASI ---
def analyze_4_indicators(prices):
    if len(prices) < 30:
        return None, "Kifayət qədər data yoxdur"

    close = prices
    
    # 1. Stochastic (14)
    low_14 = min(close[-14:])
    high_14 = max(close[-14:])
    stoch_k = 50 if high_14 == low_14 else ((close[-1] - low_14) / (high_14 - low_14)) * 100
    
    # 2. CCI (20)
    sma_tp = sum(close[-20:]) / 20
    mean_dev = sum(abs(x - sma_tp) for x in close[-20:]) / 20
    cci = 0 if mean_dev == 0 else (close[-1] - sma_tp) / (0.015 * mean_dev)

    # 3. MACD (12, 26)
    ema12 = sum(close[-12:]) / 12
    ema26 = sum(close[-26:]) / 26
    macd_line = ema12 - ema26

    # 4. Parabolic SAR Təxmini Trendi
    psar_up = close[-1] > close[-3]

    # --- SƏSVERMƏ MƏNTİQİ ---
    score = 0
    stoch_str = "Neytral ⚪️"
    cci_str = "Neytral ⚪️"
    macd_str = "Neytral ⚪️"
    psar_str = "Aşağı Trend 🔴"

    if stoch_k < 20: 
        score += 1
        stoch_str = f"{stoch_k:.1f}% (Aşırı Satış - AL) 🟢"
    elif stoch_k > 80: 
        score -= 1
        stoch_str = f"{stoch_k:.1f}% (Aşırı Alış - SAT) 🔴"

    if cci < -100: 
        score += 1
        cci_str = f"{cci:.1f} (Aşırı Satış - AL) 🟢"
    elif cci > 100: 
        score -= 1
        cci_str = f"{cci:.1f} (Aşırı Alış - SAT) 🔴"

    if macd_line > 0: 
        score += 1
        macd_str = "Yuxarı Momentum 🟢"
    elif macd_line < 0: 
        score -= 1
        macd_str = "Aşağı Momentum 🔴"

    if psar_up: 
        score += 1
        psar_str = "Yuxarı Trend 🟢"

    return score, stoch_str, cci_str, macd_str, psar_str

# --- DÜYMƏLƏR ---
def get_pair_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💶 EUR/USD", callback_data="pair_EUR/USD")
    btn2 = types.InlineKeyboardButton("💷 GBP/USD", callback_data="pair_GBP/USD")
    btn3 = types.InlineKeyboardButton("💴 USD/JPY", callback_data="pair_USD/JPY")
    btn4 = types.InlineKeyboardButton("🇦🇺 AUD/USD", callback_data="pair_AUD/USD")
    btn5 = types.InlineKeyboardButton("🇨🇦 USD/CAD", callback_data="pair_USD/CAD")
    btn6 = types.InlineKeyboardButton("🇨🇭 USD/CHF", callback_data="pair_USD/CHF")
    btn7 = types.InlineKeyboardButton("🏆 GOLD (Qızıl)", callback_data="pair_GOLD (Qızıl)")
    btn8 = types.InlineKeyboardButton("₿ BITCOIN", callback_data="pair_BITCOIN")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
    return markup

def get_time_inline_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("⏱ 1 Dəqiqə", callback_data="tf_1m")
    btn2 = types.InlineKeyboardButton("⏱ 5 Dəqiqə", callback_data="tf_5m")
    btn3 = types.InlineKeyboardButton("⏱ 15 Dəqiqə", callback_data="tf_15m")
    btn4 = types.InlineKeyboardButton("⏱ 30 Dəqiqə", callback_data="tf_30m")
    btn_back = types.InlineKeyboardButton("⬅️ BAZAR MENYUSUNA QAYIT", callback_data="back_to_pairs")
    markup.add(btn1, btn2, btn3, btn4)
    markup.add(btn_back)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "🚀 **4-İndikatorlu Binar Opsion Analiz Botu**\n\nAnaliz etmək istədiyiniz **BAZARI** aşağıdan seçin:", 
        parse_mode="Markdown", 
        reply_markup=get_pair_inline_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    data = call.data

    if data.startswith("pair_"):
        selected_pair = data.replace("pair_", "")
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

        bot.answer_callback_query(call.id, text="4 Indikator üzrə bazar təhlil olunur...")
        prices = get_market_prices(yahoo_symbol, interval=interval, range_str=range_str)

        if prices and len(prices) > 30:
            score, stoch_str, cci_str, macd_str, psar_str = analyze_4_indicators(prices)

            if score >= 3:
                final_decision = "🟢 **GÜCLÜ CALL (YUXARI) ⬆️**\n*4 indikatordan minimum 3-ü AL deyir.*"
            elif score <= -3:
                final_decision = "🔴 **GÜCLÜ PUT (AŞAĞI) ⬇️**\n*4 indikatordan minimum 3-ü SAT deyir.*"
            else:
                final_decision = "⚠️ **GÖZLƏYİN / NEUTRAL 🛑**\n*İndikatorlar arasında ziddiyyət var. Əməliyyat açmayın!*"

            msg = (
                f"📊 **4-LÜ İNDİKATOR ANALİZİ**\n"
                f"────────────────────────\n"
                f"💱 **Aktiv:** `{selected_pair}`\n"
                f"⏱ **Taymfreym:** `{tf_name}`\n"
                f"💲 **Cari Qiymət:** `{prices[-1]:.5f}`\n"
                f"────────────────────────\n"
                f"1️⃣ **Stochastic:** `{stoch_str}`\n"
                f"2️⃣ **CCI:** `{cci_str}`\n"
                f"3️⃣ **MACD:** `{macd_str}`\n"
                f"4️⃣ **Parabolic SAR:** `{psar_str}`\n"
                f"────────────────────────\n"
                f"📈 **Razılıq Səsi:** `{score} / 4`\n"
                f"🎯 **YEKUN QƏRAR:**\n{final_decision}"
            )
            bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=get_pair_inline_keyboard())
        else:
            bot.send_message(chat_id, "❌ BAZAR BAĞLIDIR və ya məlumat alınamadı.", reply_markup=get_pair_inline_keyboard())

if __name__ == "__main__":
    print("Bot uğurla işə düşdü...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            time.sleep(5)
