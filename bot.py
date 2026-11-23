"""
Trading Signal Bot - XAUUSD | XAGUSD | BTCUSD | NAS100
Timeframes: 5m | 15m
Strategy: EMA Cross + RSI + MACD confluence
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

# ====================== CONFIG ======================
SYMBOLS = {
    "XAUUSD": "GC=F",      # Gold
    "XAGUSD": "SI=F",      # Silver
    "BTCUSD": "BTC-USD",   # Bitcoin
    "NAS100": "^NDX"       # Nasdaq 100
}

TIMEFRAMES = {
    "5m":  {"interval": "5m",  "period": "5d"},
    "15m": {"interval": "15m", "period": "10d"}
}

# ====================== INDICATORS ======================
def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # EMA
    df["EMA_9"]  = df["Close"].ewm(span=9,  adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    
    # RSI
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    
    return df

def get_signal(df: pd.DataFrame) -> dict:
    if len(df) < 30:
        return {"signal": "NO DATA", "strength": 0, "price": None}
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    score = 0
    reasons = []
    
    # 1. EMA Cross
    if last["EMA_9"] > last["EMA_21"] and prev["EMA_9"] <= prev["EMA_21"]:
        score += 2
        reasons.append("EMA9 crossed ABOVE EMA21")
    elif last["EMA_9"] < last["EMA_21"] and prev["EMA_9"] >= prev["EMA_21"]:
        score -= 2
        reasons.append("EMA9 crossed BELOW EMA21")
    elif last["EMA_9"] > last["EMA_21"]:
        score += 1
        reasons.append("EMA9 > EMA21 (bullish)")
    else:
        score -= 1
        reasons.append("EMA9 < EMA21 (bearish)")
    
    # 2. RSI
    if last["RSI"] < 30:
        score += 2
        reasons.append(f"RSI Oversold ({last['RSI']:.1f})")
    elif last["RSI"] > 70:
        score -= 2
        reasons.append(f"RSI Overbought ({last['RSI']:.1f})")
    elif last["RSI"] < 45:
        score += 1
        reasons.append(f"RSI bullish zone ({last['RSI']:.1f})")
    elif last["RSI"] > 55:
        score -= 1
        reasons.append(f"RSI bearish zone ({last['RSI']:.1f})")
    
    # 3. MACD
    if last["MACD"] > last["Signal"] and prev["MACD"] <= prev["Signal"]:
        score += 2
        reasons.append("MACD bullish cross")
    elif last["MACD"] < last["Signal"] and prev["MACD"] >= prev["Signal"]:
        score -= 2
        reasons.append("MACD bearish cross")
    elif last["MACD"] > last["Signal"]:
        score += 1
        reasons.append("MACD above Signal")
    else:
        score -= 1
        reasons.append("MACD below Signal")
    
    # Final signal
    if score >= 3:
        signal = "🟢 STRONG BUY"
    elif score >= 1:
        signal = "🟢 BUY"
    elif score <= -3:
        signal = "🔴 STRONG SELL"
    elif score <= -1:
        signal = "🔴 SELL"
    else:
        signal = "⚪ NEUTRAL"
    
    return {
        "signal": signal,
        "strength": score,
        "price": round(last["Close"], 2),
        "rsi": round(last["RSI"], 1),
        "reasons": reasons
    }

# ====================== MAIN ======================
def run_bot():
    print("=" * 70)
    print(f"  TRADING SIGNAL BOT  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Instruments: XAUUSD | XAGUSD | BTCUSD | NAS100")
    print("  Timeframes: 5m | 15m")
    print("=" * 70)
    
    for name, ticker in SYMBOLS.items():
        print(f"\n{'='*70}")
        print(f"  {name}  ({ticker})")
        print(f"{'='*70}")
        
        for tf_name, tf_cfg in TIMEFRAMES.items():
            try:
                data = yf.download(
                    ticker,
                    period=tf_cfg["period"],
                    interval=tf_cfg["interval"],
                    progress=False,
                    auto_adjust=True
                )
                
                if data.empty:
                    print(f"  [{tf_name}]  No data available")
                    continue
                
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                
                data = calculate_indicators(data)
                result = get_signal(data)
                
                print(f"\n  [{tf_name}]  Price: {result['price']}  |  RSI: {result['rsi']}")
                print(f"           Signal: {result['signal']}  (Score: {result['strength']})")
                for r in result["reasons"]:
                    print(f"           • {r}")
                    
            except Exception as e:
                print(f"  [{tf_name}]  Error: {e}")
    
    print("\n" + "=" * 70)
    print("  DISCLAIMER: Educational purposes only. Not financial advice.")
    print("=" * 70)

if __name__ == "__main__":
    run_bot()
