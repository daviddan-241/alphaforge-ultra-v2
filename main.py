import requests
import time
import re
import threading
from flask import Flask

# ================= CONFIG =================
TELEGRAM_BOT_TOKEN = "8710292892:AAHGhAR_2xdkXba2wNclnyl5wOK_OjE38I4"
CHAT_ID = "5578314612"

MAX_AGE_DAYS = 5
MIN_VOLUME = 3000

BASE_URL = "https://alphaforge-ultra-v2-nngd.onrender.com"

SEEN_DISCORDS = set()
SEEN_TOKENS = set()

HEADERS = {"User-Agent": "Mozilla/5.0"}

app = Flask(__name__)

# ================= WEB =================
@app.route("/")
def home():
    return "Running 🚀"

# ================= KEEP ALIVE =================
def keep_alive():
    while True:
        try:
            requests.get(BASE_URL)
        except:
            pass
        time.sleep(600)

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ================= DISCORD =================
def extract_discord(text):
    matches = re.findall(r"https:\/\/discord\.gg\/[a-zA-Z0-9]+", text)

    clean = []
    for link in matches:
        code = link.split("/")[-1]
        if len(code) < 6:
            continue
        if link not in clean:
            clean.append(link)

    return clean

def scrape_site(url):
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        return extract_discord(html)
    except:
        return []

# ================= DEXSCREENER =================
def scan_dex():
    results = []
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs"
        pairs = requests.get(url).json().get("pairs", [])

        now = int(time.time() * 1000)
        max_age = MAX_AGE_DAYS * 86400000

        for pair in pairs:
            created = pair.get("pairCreatedAt", 0)
            if created == 0 or (now - created) > max_age:
                continue

            volume = pair.get("volume", {}).get("h24", 0)
            if volume < MIN_VOLUME:
                continue

            base = pair.get("baseToken", {})
            name = base.get("name", "Unknown")
            symbol = base.get("symbol", "")

            websites = pair.get("info", {}).get("websites", [])
            if not websites:
                continue

            website = websites[0].get("url")
            if not website:
                continue

            if website in SEEN_TOKENS:
                continue

            SEEN_TOKENS.add(website)
            results.append((name, symbol, website, volume, "DEX"))

    except:
        pass

    return results

# ================= PUMP.FUN =================
def scan_pumpfun():
    results = []
    try:
        url = "https://frontend-api.pump.fun/coins"
        coins = requests.get(url).json()

        now = int(time.time() * 1000)
        max_age = MAX_AGE_DAYS * 86400000

        for coin in coins[:100]:
            created = coin.get("created_timestamp", 0)
            if created == 0 or (now - created) > max_age:
                continue

            name = coin.get("name")
            symbol = coin.get("symbol")
            website = coin.get("website")

            if not website:
                continue

            if website in SEEN_TOKENS:
                continue

            SEEN_TOKENS.add(website)
            results.append((name, symbol, website, 0, "PUMPFUN"))

    except:
        pass

    return results

# ================= COINGECKO =================
def scan_coingecko():
    results = []
    try:
        url = "https://api.coingecko.com/api/v3/coins/list"
        coins = requests.get(url).json()

        # sample subset (API is huge)
        for coin in coins[:200]:
            name = coin.get("name")
            symbol = coin.get("symbol")

            # no direct website → skip
            continue

    except:
        pass

    return results

# ================= PROCESS =================
def process_coin(name, symbol, website, volume, source):
    links = scrape_site(website)

    if not links:
        return

    for link in links:
        if link in SEEN_DISCORDS:
            continue

        SEEN_DISCORDS.add(link)

        tag = "🔥 HIGH ACTIVITY" if volume > 10000 else "🟢 NEW"

        msg = f"""{tag} | {source}

{name} ({symbol})
🌐 {website}
💬 {link}
"""
        send(msg)
        print("Sent:", link)

# ================= BOT LOOP =================
def bot_loop():
    print("🔥 ALL-CHAIN SCANNER RUNNING")

    while True:
        try:
            for data in scan_dex():
                process_coin(*data)

            for data in scan_pumpfun():
                process_coin(*data)

        except Exception as e:
            print("Error:", e)

        time.sleep(60)

# ================= START =================
if __name__ == "__main__":
    threading.Thread(target=bot_loop).start()
    threading.Thread(target=keep_alive).start()

    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)