import requests
import time
import re

# ================= CONFIG =================
TELEGRAM_BOT_TOKEN = "8710292892:AAHGhAR_2xdkXba2wNclnyl5wOK_OjE38I4"
CHAT_ID = "5578314612"

BIRDEYE_API_KEY = "YOUR_BIRDEYE_API_KEY"

MIN_VOLUME = 2000
MAX_AGE_DAYS = 14

SEEN_DISCORDS = set()
SEEN_WEBSITES = set()
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

# ================= DEXSCREENER =================
def scan_dex():
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs"
        pairs = requests.get(url).json().get("pairs", [])

        results = []

        for pair in pairs:
            base = pair.get("baseToken", {})
            name = base.get("name", "Unknown")
            symbol = base.get("symbol", "")

            created = pair.get("pairCreatedAt", 0)
            volume = pair.get("volume", {}).get("h24", 0)

            if volume < MIN_VOLUME:
                continue

            websites = pair.get("info", {}).get("websites", [])
            if not websites:
                continue

            website = websites[0].get("url")

            if not website or website in SEEN_WEBSITES:
                continue

            SEEN_WEBSITES.add(website)

            results.append(("DEX", name, symbol, website))

        return results
    except:
        return []

# ================= BIRDEYE =================
def scan_birdeye():
    try:
        url = "https://public-api.birdeye.so/defi/tokenlist?sort_by=created_time&sort_type=desc"
        headers = {
            "X-API-KEY": BIRDEYE_API_KEY
        }

        data = requests.get(url, headers=headers).json()
        tokens = data.get("data", {}).get("tokens", [])

        results = []

        for token in tokens[:50]:
            name = token.get("name")
            symbol = token.get("symbol")
            website = token.get("website")

            if not website:
                continue

            if website in SEEN_WEBSITES:
                continue

            SEEN_WEBSITES.add(website)

            results.append(("BIRDEYE", name, symbol, website))

        return results
    except:
        return []

# ================= RAYDIUM (fallback via Dex) =================
def scan_raydium():
    # Raydium pairs are already inside Dexscreener (Solana)
    return scan_dex()

# ================= TWITTER (NITTER) =================
def scan_twitter():
    keywords = ["memecoin launch", "new token", "crypto gem"]

    results = []

    for kw in keywords:
        try:
            url = f"https://nitter.net/search?f=tweets&q={kw.replace(' ', '%20')}"
            html = requests.get(url, headers=HEADERS).text

            tweets = re.findall(r'tweet-content.*?>(.*?)</div>', html, re.DOTALL)

            for tweet in tweets:
                links = extract_discord(tweet)

                for link in links:
                    if link not in SEEN_DISCORDS:
                        results.append(("X", "Unknown", "", None, link))
        except:
            continue

    return results

# ================= PROCESS =================
def process_results(source, name, symbol, website):
    discord_links = scrape_site(website)

    for link in discord_links:
        if link in SEEN_DISCORDS:
            continue

        SEEN_DISCORDS.add(link)

        msg = f"""🚀 {source} COIN

{name} ({symbol})
🌐 {website}
💬 {link}
"""
        send(msg)
        print("Sent:", link)

# ================= MAIN =================
def run():
    print("🔥 ELITE SCANNER RUNNING (DEX + BIRDEYE + X + WEB)")

    while True:
        try:
            # ---- DEX ----
            for src, name, symbol, website in scan_dex():
                process_results(src, name, symbol, website)

            # ---- BIRDEYE ----
            for src, name, symbol, website in scan_birdeye():
                process_results(src, name, symbol, website)

            # ---- TWITTER ----
            twitter_links = scan_twitter()
            for src, name, symbol, website, link in twitter_links:
                if link not in SEEN_DISCORDS:
                    SEEN_DISCORDS.add(link)

                    msg = f"""🔥 X SIGNAL

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