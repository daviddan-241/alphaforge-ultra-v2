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

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = telebot.TeleBot(BOT_TOKEN)

seen_tokens = set()
profile_cache = {}
SEEN_FILE = "seen_tokens.json"

# ---------------- LOAD/SAVE ----------------

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

# ---------------- DISCORD ----------------

def extract_discord(links):
    if not links:
        return None
    for link in links:
        url = (link.get("url") or "").lower()
        if "discord.gg" in url or "discord.com/invite" in url:
            return link.get("url")
    return None

# ---------------- PROFILE CACHE ----------------

def load_profiles():
    global profile_cache
    try:
        r = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15)
        if r.status_code == 200:
            for p in r.json():
                profile_cache[p.get("tokenAddress")] = p
    except:
        pass

def get_discord_from_profile(addr):
    p = profile_cache.get(addr)
    if not p:
        return None
    return extract_discord(p.get("links", []))

# ---------------- SCAN ----------------

def scan():
    chains = [
        "solana","ethereum","bsc","base",
        "arbitrum","polygon","avalanche","optimism","fantom"
    ]

    sent = 0

    for chain in chains:
        try:
            url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}"
            r = requests.get(url, timeout=20)

            if r.status_code != 200:
                continue

            pairs = r.json().get("pairs", [])[:100]

            for pair in pairs:
                try:
                    base = pair.get("baseToken", {})
                    addr = base.get("address")

                    if not addr or addr in seen_tokens:
                        continue

                    liq = pair.get("liquidity", {}).get("usd", 0)
                    vol = pair.get("volume", {}).get("h24", 0)

                    if liq < 1000:
                        continue

                    discord = extract_discord(pair.get("info", {}).get("socials", []))
                    if not discord:
                        discord = get_discord_from_profile(addr)

                    if not discord:
                        continue

                    seen_tokens.add(addr)
                    save_seen()

                    name = base.get("name", "Unknown")
                    symbol = base.get("symbol", "?")
                    chart = pair.get("url")

                    msg = (
                        f"🚀 Coin with Discord\n\n"
                        f"{name} ({symbol})\n"
                        f"Chain: {chain.upper()}\n\n"
                        f"💧 Liquidity: ${liq:,.0f}\n"
                        f"📊 Volume: ${vol:,.0f}\n\n"
                        f"🔗 {discord}\n"
                        f"📈 {chart}"
                    )

                    bot.send_message(USER_CHAT_ID, msg)
                    print("Sent:", name)
                    sent += 1

                except Exception as e:
                    print("Pair error:", e)

        except Exception as e:
            print("Chain error:", e)

    print("Done. Sent:", sent)

# ---------------- START ----------------

def start():
    load_profiles()

    bot.send_message(USER_CHAT_ID, "✅ Bot started and scanning...")

    sched = BackgroundScheduler()
    sched.add_job(scan, "interval", minutes=5)
    sched.start()

    for i in range(2):
        scan()
        time.sleep(5)

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "OK", 200

@app.route("/test")
def test():
    bot.send_message(USER_CHAT_ID, "🔥 Test OK")
    return "sent"

# ---------------- MAIN ----------------

if __name__ == "__main__":
    load_seen()
    threading.Thread(target=start, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)