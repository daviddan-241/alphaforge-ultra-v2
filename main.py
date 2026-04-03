import os
import threading
import time
import json
import requests
from flask import Flask
import telebot
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
USER_CHAT_ID = int(os.environ.get("USER_CHAT_ID", "5578314612"))
SEEN_FILE = "seen_tokens.json"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required")

bot = telebot.TeleBot(BOT_TOKEN)

seen_tokens = set()
profile_cache = {}

# ------------------ STORAGE ------------------

def load_seen():
    global seen_tokens
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen_tokens = set(json.load(f))
        except:
            seen_tokens = set()

def save_seen():
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_tokens), f)
    except:
        pass

# ------------------ DISCORD EXTRACTION ------------------

def extract_discord(links):
    if not links:
        return None
    for link in links:
        url = (link.get("url") or "").lower()
        if "discord.gg" in url or "discord.com/invite" in url:
            return link.get("url")
    return None

# ------------------ PROFILE FALLBACK ------------------

def load_profiles():
    global profile_cache
    try:
        resp = requests.get(
            "https://api.dexscreener.com/token-profiles/latest/v1",
            timeout=15
        )
        if resp.status_code == 200:
            for p in resp.json():
                profile_cache[p.get("tokenAddress")] = p
    except:
        pass

def get_discord_from_profile(token_addr):
    profile = profile_cache.get(token_addr)
    if not profile:
        return None
    return extract_discord(profile.get("links", []))

# ------------------ SCANNER ------------------

def scan_coins():
    global seen_tokens

    chains = [
        "solana",
        "ethereum",
        "bsc",
        "base",
        "arbitrum",
        "polygon",
        "avalanche",
        "optimism",
        "fantom"
    ]

    sent = 0

    for chain in chains:
        try:
            url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}"
            resp = requests.get(url, timeout=20)

            if resp.status_code != 200:
                continue

            pairs = resp.json().get("pairs", [])[:120]

            for pair in pairs:
                try:
                    base = pair.get("baseToken", {})
                    token_addr = base.get("address")

                    if not token_addr or token_addr in seen_tokens:
                        continue

                    liquidity = pair.get("liquidity", {}).get("usd", 0)
                    volume = pair.get("volume", {}).get("h24", 0)
                    price_change = pair.get("priceChange", {}).get("h24", 0)

                    # FILTER REAL COINS
                    if liquidity < 5000 or volume < 1000:
                        continue

                    if price_change < -60:
                        continue

                    # DISCORD CHECK
                    discord = extract_discord(
                        pair.get("info", {}).get("socials", [])
                    )

                    if not discord:
                        discord = get_discord_from_profile(token_addr)

                    if not discord:
                        continue

                    seen_tokens.add(token_addr)
                    save_seen()

                    name = base.get("name", "Unknown")
                    symbol = base.get("symbol", "???")
                    dex_url = pair.get("url")

                    message = (
                        f"🚀 New ACTIVE Coin with Discord\n\n"
                        f"Name: {name}\n"
                        f"Symbol: {symbol}\n"
                        f"Chain: {chain.upper()}\n\n"
                        f"💧 Liquidity: ${liquidity:,.0f}\n"
                        f"📊 Volume (24h): ${volume:,.0f}\n\n"
                        f"🔗 Discord: {discord}\n"
                        f"📈 Chart: {dex_url}\n\n"
                        f"⚡ Filtered Alpha"
                    )

                    bot.send_message(USER_CHAT_ID, message)
                    print(f"✅ Sent {name} ({chain})")
                    sent += 1

                except Exception as e:
                    print("Pair error:", e)

        except Exception as e:
            print("Chain error:", e)

    print(f"Scan complete — sent {sent} coins")

# ------------------ SCHEDULER ------------------

def start_scheduler():
    load_profiles()

    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_coins, "interval", minutes=5)
    scheduler.start()

    print("🚀 Bot started — scanning every 5 minutes")

    # Initial boost scan
    for i in range(3):
        print(f"Initial scan round {i+1}")
        scan_coins()
        time.sleep(10)

# ------------------ WEB SERVER ------------------

@app.route("/")
def home():
    return "✅ Coin Discord Scanner Running"

# ------------------ MAIN ------------------

if __name__ == "__main__":
    load_seen()

    thread = threading.Thread(target=start_scheduler)
    thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)