# -*- coding: utf-8 -*-
import json
import time
import urllib.request
import math

TELEGRAM_TOKEN = "8911527218:AAE1IQ-lNNk7tw3m03OJgIFM5OSvkjncxaI"
CHAT_ID = "7508094911"

MARKETS = {
    "1": ("EUR/USD", "EURUSD=X"),
    "2": ("GBP/USD", "GBPUSD=X"),
    "3": ("USD/JPY", "JPY=X"),
    "4": ("AUD/USD", "AUDUSD=X"),
    "5": ("USD/CAD", "CAD=X"),
    "6": ("GOLD (Qızıl)", "GC=F")
}

TIMEFRAMES = {
    "1": ("1 Dəqiqə", "1m", "1d"),
    "2": ("5 Dəqiqə", "5m", "1d"),
    "3": ("15 Dəqiqə", "15m", "5d"),
    "4": ("30 Dəqiqə", "30m", "5d"),
    "5": ("1 Saat", "60m", "1mo"),
    "6": ("4 Saat", "60m", "1mo")
}

def send_telegram(text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode() == 200
    except Exception as e:
        print(f"Telegram Xətası: {e}")
        return False

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=10"
    if offset:
        url += f"&offset={offset}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode()).get("result", [])
    except:
        return []

def fetch_data(symbol_code, interval, period):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_code}?interval={interval}&range={period}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            raw = json.loads(response.read().decode())
            quote = raw['chart']['result'][0]['indicators']['quote'][0]
            closes, highs, lows = [], [], []
            for i in range(len(quote['close'])):
                c, h, l = quote['close'][i], quote['high'][i], quote['low'][i]
                if c is not None and h is not None and l is not None:
                    closes.append(c)
                    highs.append(h)
                    lows.append(l)
            return closes, highs, lows
    except Exception as e:
        print(f"Bazar məlumat xətası: {e}")
        return [], [], []

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        chg = closes[i] - closes[i-1]
        gains.append(chg if chg > 0 else 0)
        losses.append(abs(chg) if chg < 0 else 0)
    avg_g = sum(gains[-period:]) / period
    avg_l = sum(losses[-period:]) / period
    if avg_l == 0: return 100
    return 100 - (100 / (1 + (avg_g / avg_l)))

def calc_ema(values, span):
    k = 2 / (span + 1)
    ema = values[0]
    for val in values[1:]:
        ema = (val * k) + (ema * (1 - k))
    return ema

def calc_macd(closes):
    if len(closes) < 26: return "NEUTRAL"
    ema12 = calc_ema(closes[-26:], 12)
    ema26 = calc_ema(closes[-26:], 26)
    return "CALL" if (ema12 - ema26) > 0 else "PUT"

def calc_sma(closes, period):
    if len(closes) < period: return closes[-1]
    return sum(closes[-period:]) / period

def calc_bollinger(closes, period=20):
    if len(closes) < period: return "NEUTRAL"
    sma = calc_sma(closes, period)
    sub = closes[-period:]
    std = math.sqrt(sum((x - sma) ** 2 for x in sub) / period)
    curr = closes[-1]
    if curr <= sma - (2 * std): return "CALL"
    elif curr >= sma + (2 * std): return "PUT"
    return "NEUTRAL"

def calc_stochastic(closes, highs, lows, period=14):
    if len(closes) < period: return "NEUTRAL"
    c_sub, h_sub, l_sub = closes[-period:], highs[-period:], lows[-period:]
    lowest_l, highest_h = min(l_sub), max(h_sub)
    if highest_h == lowest_l: return "NEUTRAL"
    k = 100 * ((c_sub[-1] - lowest_l) / (highest_h - lowest_l))
    if k < 20: return "CALL"
    elif k > 80: return "PUT"
    return "NEUTRAL"

def calc_cci(closes, highs, lows, period=20):
    if len(closes) < period: return "NEUTRAL"
    tps = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(-period, 0)]
    sma_tp = sum(tps) / period
    mad = sum(abs(x - sma_tp) for x in tps) / period
    if mad == 0: return "NEUTRAL"
    cci = (tps[-1] - sma_tp) / (0.015 * mad)
    if cci < -100: return "CALL"
    elif cci > 100: return "PUT"
    return "NEUTRAL"

def analyze_market(closes, highs, lows):
    signals = {}
    rsi = calc_rsi(closes)
    signals['RSI (14)'] = ('YUXARI ⬆️', 'CALL') if rsi < 35 else (('AŞAĞI ⬇️', 'PUT') if rsi > 65 else ('NEYTRAL ⏹', 'NEUTRAL'))
    
    macd_res = calc_macd(closes)
    signals['MACD'] = ('YUXARI ⬆️', 'CALL') if macd_res == "CALL" else (('AŞAĞI ⬇️', 'PUT') if macd_res == "PUT" else ('NEYTRAL ⏹', 'NEUTRAL'))

    sma10, sma20 = calc_sma(closes, 10), calc_sma(closes, 20)
    signals['Moving Average'] = ('YUXARI ⬆️', 'CALL') if sma10 > sma20 else (('AŞAĞI ⬇️', 'PUT') if sma10 < sma20 else ('NEYTRAL ⏹', 'NEUTRAL'))

    bb_res = calc_bollinger(closes)
    signals['Bollinger Bands'] = ('YUXARI ⬆️', 'CALL') if bb_res == "CALL" else (('AŞAĞI ⬇️', 'PUT') if bb_res == "PUT" else ('NEYTRAL ⏹', 'NEUTRAL'))

    stoch_res = calc_stochastic(closes, highs, lows)
    signals['Stochastic'] = ('YUXARI ⬆️', 'CALL') if stoch_res == "CALL" else (('AŞAĞI ⬇️', 'PUT') if stoch_res == "PUT" else ('NEYTRAL ⏹', 'NEUTRAL'))

    cci_res = calc_cci(closes, highs, lows)
    signals['CCI (20)'] = ('YUXARI ⬆️', 'CALL') if cci_res == "CALL" else (('ASHAGI ⬇️', 'PUT') if cci_res > 100 else ('NEYTRAL ⏹', 'NEUTRAL'))

    return signals, closes[-1]

def show_market_menu():
    keyboard = {
        "inline_keyboard": [
            [{"text": "1. EUR/USD", "callback_data": "m_1"}, {"text": "2. GBP/USD", "callback_data": "m_2"}],
            [{"text": "3. USD/JPY", "callback_data": "m_3"}, {"text": "4. AUD/USD", "callback_data": "m_4"}],
            [{"text": "5. USD/CAD", "callback_data": "m_5"}, {"text": "6. GOLD (Qızıl)", "callback_data": "m_6"}]
        ]
    }
    send_telegram("📊 **Analiz etmək istədiyiniz BAZARI seçin:**", keyboard)

def show_timeframe_menu(market_key):
    keyboard = {
        "inline_keyboard": [
            [{"text": "1 Dəqiqə", "callback_data": f"t_{market_key}_1"}, {"text": "5 Dəqiqə", "callback_data": f"t_{market_key}_2"}],
            [{"text": "15 Dəqiqə", "callback_data": f"t_{market_key}_3"}, {"text": "30 Dəqiqə", "callback_data": f"t_{market_key}_4"}],
            [{"text": "1 Saat", "callback_data": f"t_{market_key}_5"}, {"text": "4 Saat", "callback_data": f"t_{market_key}_6"}]
        ]
    }
    send_telegram(f"⏱ **{MARKETS[market_key][0]}** üçün **TAYMFREYM** seçin:", keyboard)

def main():
    print("PythonAnywhere-də Bot Aktivdir!")
    send_telegram("🚀 **Manual Analiz Botu Serverdə Aktivləşdirildi!**")
    show_market_menu()
    
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "callback_query" in update:
                data = update["callback_query"]["data"]
                if data.startswith("m_"):
                    show_timeframe_menu(data.split("_")[1])
                elif data.startswith("t_"):
                    _, m_k, t_k = data.split("_")
                    m_name, m_code = MARKETS[m_k]
                    t_name, interval, period = TIMEFRAMES[t_k]
                    send_telegram(f"⏳ **{m_name}** ({t_name}) canlı bazarı analiz olunur...")
                    closes, highs, lows = fetch_data(m_code, interval, period)
                    if len(closes) > 25:
                        signals, curr_price = analyze_market(closes, highs, lows)
                        up = sum(1 for v in signals.values() if v[1] == 'CALL')
                        down = sum(1 for v in signals.values() if v[1] == 'PUT')
                        decision = "🟢 **CALL (YUXARI)**" if up >= 3 else ("🔴 **PUT (AŞAĞI)**" if down >= 3 else "⚪️ **NEYTRAL**")
                        report = f"📊 **{m_name} ({t_name})**\n💵 **Qiymət:** {curr_price:.5f}\n\n"
                        for ind, val in signals.items():
                            report += f"• {ind}: {val[0]}\n"
                        report += f"\n{decision}"
                        send_telegram(report)
                        time.sleep(1)
                        show_market_menu()
            elif "message" in update and update["message"].get("text") == "/start":
                show_market_menu()
        time.sleep(1)

if __name__ == "__main__":
    main()
