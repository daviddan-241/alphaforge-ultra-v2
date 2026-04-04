import requests
import time
import re
import threading
from flask import Flask

# ================= CONFIG =================
TELEGRAM_BOT_TOKEN = "8710292892:AAHGhAR_2xdkXba2wNclnyl5wOK_OjE38I4"
CHAT_ID = "5578314612"

MIN_VOLUME = 2000
MAX_AGE_DAYS = 5

# 👉 REPLACE WITH YOUR RENDER URL
BASE_URL = "https://alphaforge-ultra-v2-nngd.onrender.com"

SEEN_DISCORDS = set()
SEEN_TOKENS = set()

HEADERS = {"User-Agent": "Mozilla/5.0"}

app = Flask(__name__)

# ================= WEB SERVER =================
@app.route("/")
def home():
    return "Bot is alive 🚀"

# ================= KEEP ALIVE =================
def keep_alive():
    while True:
        try:
            requests.get(BASE_URL)
            print("🔄 Self ping sent")
        except:
            print("❌ Ping failed")
        time.sleep(600)  # every 10 minutes

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ================= DISCORD =================
def extract_discord(text):
    return re.findall(r"https:\/\/discord\.gg\/[a-zA-Z0-9]+", text)

def scrape_site(url):
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        return extract_discord(html)
    except:
        return []

# ================= DEX =================
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
            results.append((name, symbol, website))
    except:
        pass

    return results

# ================= PUMPFUN =================
def scan_pumpfun():
    results = []
    try:
        url = "https://frontend-api.pump.fun/coins"
        coins = requests.get(url).json()

        now = int(time.time() * 1000)
        max_age = MAX_AGE_DAYS * 86400000

        for coin in coins[:50]:
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
            results.append((name, symbol, website))
    except:
        pass

    return results

# ================= X =================
def scan_x():
    results = []
    keywords = ["memecoin launch", "pumpfun", "new token"]

    for kw in keywords:
        try:
            url = f"https://nitter.net/search?f=tweets&q={kw.replace(' ', '%20')}"
            html = requests.get(url, headers=HEADERS).text

            tweets = re.findall(r'tweet-content.*?>(.*?)</div>', html, re.DOTALL)

            for tweet in tweets:
                links = extract_discord(tweet)

                for link in links:
                    if link not in SEEN_DISCORDS:
                        results.append(link)
        except:
            continue

    return results

# ================= BOT LOOP =================
def bot_loop():
    print("🔥 Bot running (Keep Alive Mode)")

    while True:
        try:
            for name, symbol, website in scan_dex():
                for link in scrape_site(website):
                    if link not in SEEN_DISCORDS:
                        SEEN_DISCORDS.add(link)
                        send(f"🚀 DEX\n{name} ({symbol})\n🌐 {website}\n💬 {link}")

            for name, symbol, website in scan_pumpfun():
                for link in scrape_site(website):
                    if link not in SEEN_DISCORDS:
                        SEEN_DISCORDS.add(link)
                        send(f"🚀 PUMPFUN\n{name} ({symbol})\n🌐 {website}\n💬 {link}")

            for link in scan_x():
                if link not in SEEN_DISCORDS:
                    SEEN_DISCORDS.add(link)
                    send(f"🔥 X SIGNAL\n💬 {link}")

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