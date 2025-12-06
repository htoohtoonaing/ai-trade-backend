
from flask import Flask, jsonify, request
import os
import requests
import random

app = Flask(__name__)

# ==============================
# ENV VAR (Render → Environment)
# ==============================
OANDA_API_KEY = os.environ.get("OANDA_API_KEY", "09bd435e45ad42bf3d66799397a669d1-6eb68acbbdf10be074d648a09397d2af")

# ==============================
# OTC → OANDA Pair Map
# ==============================
PAIR_MAP = {
    "EURUSD_OTC": "EUR_USD",
    "EURJPY_OTC": "EUR_JPY",
    "EURGBP_OTC": "EUR_GBP",
    "EURCHF_OTC": "EUR_CHF",
    "GBPUSD_OTC": "GBP_USD",
    "GBPJPY_OTC": "GBP_JPY",
    "USDJPY_OTC": "USD_JPY",
    "USDCAD_OTC": "USD_CAD",
    "USDCHF_OTC": "USD_CHF",
    "AUDUSD_OTC": "AUD_USD",
    "AUDJPY_OTC": "AUD_JPY",
    "NZDUSD_OTC": "NZD_USD",
    "NZDJPY_OTC": "NZD_JPY",
    # လိုသလို ထပ်ထည့်လို့ရ
}


# ==============================
# OANDA Candle Fetch
# ==============================
def fetch_oanda_candles(otc_pair: str, granularity: str = "S5", count: int = 100):
    """OANDA မှ candles ကို practice API ကနေယူမယ်. မရရင် None ပြန်မယ်."""
    if not OANDA_API_KEY:
        return None

    instrument = PAIR_MAP.get(otc_pair)
    if not instrument:
        return None

    url = f"https://api-fxpractice.oanda.com/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {
        "count": count,
        "granularity": granularity,
        "price": "M",
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        r.raise_for_status()
        candles = r.json().get("candles", [])
        closes = [float(c["mid"]["c"]) for c in candles if c.get("mid")]
        if not closes:
            return None
        return closes
    except Exception:
        return None


# ==============================
# Fake Candle Generator (fallback)
# ==============================
def fake_candles(count: int = 100, base: float = 1.0850):
    prices = []
    last = base
    for _ in range(count):
        change = (random.random() - 0.5) * 0.002
        last = last + change
        prices.append(last)
    return prices


# ==============================
# RSI Calculation
# ==============================
def calc_rsi(closes, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-diff)

    recent_gains = gains[-period:]
    recent_losses = losses[-period:]

    avg_gain = sum(recent_gains) / period
    avg_loss = sum(recent_losses) / period if sum(recent_losses) != 0 else 1e-6

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


# ==============================
# Simple AI Logic from RSI
# ==============================
def decision_from_rsi(rsi: float):
    """
    RSI ကနေ BUY / SELL / HOLD + confidence + note ထုတ်ပေးမယ်
    """
    if rsi >= 70:
        return "SELL", random.randint(82, 95), "Overbought zone – downside correction likely."
    elif rsi <= 30:
        return "BUY", random.randint(82, 95), "Oversold zone – bounce upward likely."
    elif 55 <= rsi < 70:
        return "SELL", random.randint(60, 80), "Mildly overbought – short-term sell bias."
    elif 30 < rsi <= 45:
        return "BUY", random.randint(60, 80), "Mildly oversold – buy-on-dip bias."
    else:
        return "HOLD", 0, "Sideways / mixed signals – neutral."


# ==============================
# Root
# ==============================
@app.route("/")
def root():
    return jsonify({"status": "OK", "msg": "AI GPT Trade Bot Backend"}), 200


# ==============================
# MAIN SIGNAL API
# ==============================
@app.route("/signal_api/signal")
def signal_api():
    pair = request.args.get("pair", "EURUSD_OTC")
    timeframe = request.args.get("timeframe", "5s")

    closes = fetch_oanda_candles(pair)
    used_source = "oanda"

    if not closes:
        closes = fake_candles()
        used_source = "local_fake"

    rsi = calc_rsi(closes)
    signal, confidence, note = decision_from_rsi(rsi)

    return jsonify(
        {
            "pair": pair,
            "timeframe": timeframe,
            "data_points": len(closes),
            "rsi": rsi,
            "signal": signal,  # BUY / SELL / HOLD
            "confidence": confidence,
            "note": note,
            "source": used_source,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
