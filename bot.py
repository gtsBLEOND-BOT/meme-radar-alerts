
import os
import json
import urllib.request
import urllib.parse

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

API = "https://api.dexscreener.com"
SEEN_FILE = "seen_tokens.json"

# Fillojmë me kritere të rrepta; mund t'i rregullojmë më vonë.
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
        return json.loads(response.read().decode("utf-8"))


def main():
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            seen = set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        seen = set()

    profiles = get_json(f"{API}/token-profiles/latest/v1")
    if not isinstance(profiles, list):
        profiles = [profiles]

    candidates = []
    checked = set()

    for profile in profiles[:100]:
        chain = profile.get("chainId")
        address = profile.get("tokenAddress")
        if not chain or not address:
            continue

        key = f"{chain}:{address}".lower()
        if key in seen or key in checked:
            continue
        checked.add(key)

        try:
            pairs = get_json(
                f"{API}/token-pairs/v1/{chain}/{address}"
            )
        except Exception:
            continue

        if not isinstance(pairs, list) or not pairs:
            continue

        # Vlerësojmë çiftin me likuiditetin më të madh.
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

        import time
        age_hours = (time.time() * 1000 - created) / 3600000

        # Filtra bazë: nuk është audit i kontratës.
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
        link = pair.get("url") or profile.get("url") or ""

        candidates.append(
            f"🟡 KANDIDAT I RI — DUHET VERIFIKUAR\n"
            f"{name} ({symbol})\n"
            f"Rrjeti: {chain}\n"
            f"Çmimi: ${price}\n"
            f"Likuiditeti: ${liquidity:,.0f}\n"
            f"Volumi 24h: ${volume:,.0f}\n"
            f"Transaksione 1h: {txn_count}\n"
            f"Mosha e çiftit: {age_hours:.1f} orë\n"
            f"⚠️ Filtrat nuk garantojnë siguri; kontrollo kontratën.\n"
            f"{link}"
        )
        seen.add(key)

    for candidate in candidates:
        send_telegram(candidate)

    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)


if __name__ == "__main__":
    main()
