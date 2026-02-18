import pandas as pd
import numpy as np
import time
import requests
from flask import Flask
from threading import Thread
import os

# --- కాన్ఫిగరేషన్ ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN') or '8555099542:AAEzc0msQey6qvBMTylqqfSclpWc8pMUzm4'
CHAT_ID = os.environ.get('CHAT_ID') or '5356787589'

app = Flask('')
@app.route('/')
def home(): return "Binance Top 100 Bot is Active!"

def send_telegram_msg(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

# టాప్ 100 కాయిన్స్ లిస్ట్ తీసుకోవడం
def get_top_100_symbols():
    try:
        # వాల్యూమ్ బట్టి టాప్ కాయిన్స్ ని ఫిల్టర్ చేయడానికి 
        url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
        response = requests.get(url, timeout=10)
        data = response.json()
        # USDT పెయిర్స్ ని వాల్యూమ్ ఆధారంగా సార్ట్ చేయడం
        sorted_data = sorted([d for d in data if d['symbol'].endswith('USDT')], 
                            key=lambda x: float(x['quoteVolume']), reverse=True)
        return [d['symbol'] for d in sorted_data[:100]]
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

def get_binance_data(symbol, timeframe='15m'):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={timeframe}&limit=100"
        response = requests.get(url, timeout=10)
        df = pd.DataFrame(response.json(), columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 'nt', 'tbv', 'tqv', 'i'])
        df[['close', 'high', 'low']] = df[['close', 'high', 'low']].astype(float)
        return df
    except: return None

def apply_indicators(df):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    return df

def scan_top_100():
    symbols = get_top_100_symbols()
    for s in symbols:
        df_1h = get_binance_data(s, '1h')
        df_15m = get_binance_data(s, '15m')
        
        if df_1h is not None and df_15m is not None:
            df_1h = apply_indicators(df_1h)
            df_15m = apply_indicators(df_15m)
            
            trend_1h = "BULLISH" if df_1h['close'].iloc[-1] > df_1h['SMA_50'].iloc[-1] else "BEARISH"
            last_15m = df_15m.iloc[-1]

            # Strategy Logic
            if trend_1h == "BULLISH" and last_15m['RSI'] < 38:
                price = last_15m['close']
                msg = (f"🚀 *TOP 100 BUY ALERT* 🚀\n\n*Coin:* {s}\n*Price:* {price}\n"
                       f"*RSI:* {round(last_15m['RSI'], 2)}\n"
                       f"🛡️ *SL:* {round(price*0.985, 2)} | 🎯 *TP:* {round(price*1.05, 2)}")
                send_telegram_msg(msg)

            elif trend_1h == "BEARISH" and last_15m['RSI'] > 62:
                price = last_15m['close']
                msg = (f"⚠️ *TOP 100 SELL ALERT* ⚠️\n\n*Coin:* {s}\n*Price:* {price}\n"
                       f"*RSI:* {round(last_15m['RSI'], 2)}\n"
                       f"🛡️ *SL:* {round(price*1.015, 2)} | 🎯 *TP:* {round(price*0.95, 2)}")
                send_telegram_msg(msg)
        time.sleep(0.3)

def main_loop():
    send_telegram_msg("🔝 *Binance Top 100 Volume Bot Active!* \nScanning high-liquidity coins...")
    while True:
        scan_top_100()
        time.sleep(60)

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    main_loop()
