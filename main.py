import requests
import time
import re

# ================= CONFIG =================
TELEGRAM_BOT_TOKEN = "8710292892:AAHGhAR_2xdkXba2wNclnyl5wOK_OjE38I4"
CHAT_ID = "5578314612"

MIN_VOLUME = 2000
MAX_AGE_DAYS = 5

SEEN_DISCORDS = set()
SEEN_TOKENS = set()

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ================= TELEGRAM =================
def send(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# ================= DISCORD EXTRACT =================
def extract_discord(text):
    return re.findall(r"https:\/\/discord\.gg\/[a-zA-Z0-9]+", text)

# ================= WEBSITE SCRAPER =================
def scrape_site(url):
    try:
        html = requests.get(url, headers=HEADERS, timeout=10).text
        return extract_discord(html)
    except:
        return []

# ================= DEX (ALL CHAINS) =================
def scan_dex():
    results = []
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs"
        pairs = requests.get(url, timeout=10).json().get("pairs", [])

        now = int(time.time() * 1000)
        max_age_ms = MAX_AGE_DAYS * 24 * 60 * 60 * 1000

        for pair in pairs:
            created = pair.get("pairCreatedAt", 0)
            if created == 0:
                continue

            age = now - created
            if age > max_age_ms:
                continue  # ❌ older than 5 days

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

            token_id = website
            if token_id in SEEN_TOKENS:
                continue

            SEEN_TOKENS.add(token_id)

            results.append((name, symbol, website))

    except:
        pass

    return results

# ================= PUMP.FUN =================
def scan_pumpfun():
    results = []
    try:
        url = "https://frontend-api.pump.fun/coins"
        coins = requests.get(url, timeout=10).json()

        now = int(time.time() * 1000)
        max_age_ms = MAX_AGE_DAYS * 86400000

        for coin in coins[:50]:
            created = coin.get("created_timestamp", 0)
            if created == 0:
                continue

            age = now - created
            if age > max_age_ms:
                continue  # ❌ older than 5 days

            name = coin.get("name")
            symbol = coin.get("symbol")
            website = coin.get("website")

            if not website:
                continue

            token_id = website
            if token_id in SEEN_TOKENS:
                continue

            SEEN_TOKENS.add(token_id)

            results.append((name, symbol, website))

    except:
        pass

    return results

# ================= X SCAN =================
def scan_x():
    results = []
    keywords = ["pumpfun", "memecoin launch", "new token"]

    for kw in keywords:
        try:
            url = f"https://nitter.net/search?f=tweets&q={kw.replace(' ', '%20')}"
            html = requests.get(url, headers=HEADERS, timeout=10).text

            tweets = re.findall(r'tweet-content.*?>(.*?)</div>', html, re.DOTALL)

            for tweet in tweets:
                links = extract_discord(tweet)

                for link in links:
                    if link not in SEEN_DISCORDS:
                        results.append(link)

        except:
            continue

    return results

# ================= PROCESS =================
def process_coin(source, name, symbol, website):
    try:
        discord_links = scrape_site(website)

        if not discord_links:
            return  # ❌ STRICT: must have Discord

        for link in discord_links:
            if link in SEEN_DISCORDS:
                continue

            SEEN_DISCORDS.add(link)

            msg = f"""🚀 {source} (≤5 DAYS)

{name} ({symbol})
🌐 {website}
💬 {link}
"""
            send(msg)
            print("Sent:", link)

    except:
        pass

# ================= MAIN =================
def run():
    print("🔥 5-DAY DISCORD SCANNER RUNNING")

    while True:
        try:
            # ---- DEX ----
            for name, symbol, website in scan_dex():
                process_coin("DEX", name, symbol, website)

            # ---- PUMPFUN ----
            for name, symbol, website in scan_pumpfun():
                process_coin("PUMPFUN", name, symbol, website)

            # ---- X ----
            for link in scan_x():
                if link not in SEEN_DISCORDS:
                    SEEN_DISCORDS.add(link)

                    msg = f"""🔥 X SIGNAL (FRESH)

💬 {link}
"""
                    send(msg)
                    print("X:", link)

        except Exception as e:
            print("Error:", e)

        time.sleep(60)

# ================= START =================
if __name__ == "__main__":
    run()