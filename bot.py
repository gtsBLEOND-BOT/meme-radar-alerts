
import os
import json
import time
import urllib.request
import urllib.parse

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API = "https://api.dexscreener.com"
SEEN_FILE = "seen_tokens.json"

MIN_LIQUIDITY_USD = 20000
MIN_VOLUME_24H_USD = 50000
MIN_TXNS_1H = 50
MAX_TOKEN_AGE_HOURS = 48

def get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "MemeRadarAlerts/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true"
    }).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError("Telegram send failed")

def main():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            seen = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        seen = set()

    sources = [
        f"{API}/token-profiles/latest/v1",
        f"{API}/token-boosts/latest/v1",
    ]

    candidates = {}
    checked = set()

    for source in sources:
        try:
            data = get_json(source)
            if not isinstance(data, list):
                continue
        except Exception as e:
            print(f"Source error: {e}")
            continue

        for item in data:
            chain = item.get("chainId")
            address = item.get("tokenAddress")
            if not chain or not address:
                continue

            key = f"{chain}:{address}".lower()
            if key not in seen:
                candidates[key] = (chain, address)

    for key, (chain, address) in candidates.items():
        if key in checked:
            continue
        checked.add(key)

        try:
            pairs = get_json(
                f"{API}/token-pairs/v1/{chain}/{address}"
            )
        except Exception as e:
            print(f"Pair lookup error: {e}")
            continue

        if not isinstance(pairs, list) or not pairs:
            continue

        pair = max(
            pairs,
            key=lambda p: (p.get("liquidity") or {}).get("usd") or 0
        )

        liquidity = (pair.get("liquidity") or {}).get("usd") or 0
        volume = (pair.get("volume") or {}).get("h24") or 0
        txns = (pair.get("txns") or {}).get("h1") or {}
        txn_count = (txns.get("buys") or 0) + (txns.get("sells") or 0)
        created = pair.get("pairCreatedAt")

        if not created:
            continue

        age_hours = (time.time() * 1000 - created) / 3600000

        if not (0 <= age_hours <= MAX_TOKEN_AGE_HOURS):
            continue
        if liquidity < MIN_LIQUIDITY_USD:
            continue
        if volume < MIN_VOLUME_24H_USD:
            continue
        if txn_count < MIN_TXNS_1H:
            continue

        token = pair.get("baseToken") or {}
        name = token.get("name") or "Unknown"
        symbol = token.get("symbol") or "?"
        price = pair.get("priceUsd") or "N/A"
        link = pair.get("url") or (
            f"https://dexscreener.com/{chain}/{address}"
        )

        message = (
            "🟡 KANDIDAT I RI — KONTROLLOJE\n"
            f"{name} ({symbol})\n"
            f"Rrjeti: {chain}\n"
            f"Çmimi: ${price}\n"
            f"Likuiditeti: ${liquidity:,.0f}\n"
            f"Volumi 24h: ${volume:,.0f}\n"
            f"Transaksione 1h: {txn_count}\n"
            f"Mosha e çiftit: {age_hours:.1f} orë\n"
            "⚠️ Filtrat nuk garantojnë siguri. Kontrollo kontratën, "
            "holder-at dhe mundësinë e shitjes.\n"
            f"{link}"
        )

        try:
            send_telegram(message)
            seen.add(key)
            print(f"Alert sent: {chain}:{address}")
        except Exception as e:
            print(f"Telegram error: {e}")

    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)

if __name__ == "__main__":
    main()
    
