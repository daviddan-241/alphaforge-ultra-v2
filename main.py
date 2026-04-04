import os
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
    raise Exception("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN)

SEEN_FILE = "seen.json"
seen = set()

# ---------------- LOAD SEEN ----------------

if os.path.exists(SEEN_FILE):
    try:
        with open(SEEN_FILE, "r") as f:
            seen = set(json.load(f))
    except:
        seen = set()

def save_seen():
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen), f)
    except:
        pass

# ---------------- DISCORD EXTRACT ----------------

def extract_discord(text):
    if not text:
        return None

    text = str(text).lower()

    for word in text.split():
        if "discord.gg" in word or "discord.com/invite" in word:
            return word.strip()

    return None

# ---------------- SEND SAFE ----------------

def send(msg):
    try:
        bot.send_message(USER_CHAT_ID, msg)
    except Exception as e:
        print("Send error:", e)

# ---------------- DEX SCAN ----------------

def scan_dex():
    found = 0
    try:
        url = "https://api.dexscreener.com/latest/dex/pairs/solana"
        r = requests.get(url, timeout=15)

        if r.status_code != 200:
            print("Dex failed")
            return 0

        pairs = r.json().get("pairs", [])[:80]

        for p in pairs:
            addr = p.get("baseToken", {}).get("address")

            if not addr or addr in seen:
                continue

            discord = extract_discord(p)

            if not discord:
                continue

            seen.add(addr)
            save_seen()

            name = p.get("baseToken", {}).get("symbol", "TOKEN")

            msg = f"🚀 {name} (SOL)\n\n🔗 {discord}"

            send(msg)
            print("DEX SENT:", name)
            found += 1

    except Exception as e:
        print("Dex error:", e)

    return found

# ---------------- BIRDEYE SCAN ----------------

def scan_birdeye():
    found = 0
    try:
        url = "https://public-api.birdeye.so/defi/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=50"
        headers = {"x-chain": "solana"}

        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            print("Birdeye failed")
            return 0

        tokens = r.json().get("data", {}).get("tokens", [])

        for t in tokens:
            addr = t.get("address")

            if not addr or addr in seen:
                continue

            discord = extract_discord(t)

            if not discord:
                continue

            seen.add(addr)
            save_seen()

            name = t.get("symbol", "SOL")

            msg = f"🔥 {name} (Birdeye)\n\n🔗 {discord}"

            send(msg)
            print("BIRDEYE SENT:", name)
            found += 1

    except Exception as e:
        print("Birdeye error:", e)

    return found

# ---------------- FALLBACK ----------------

fallback_links = [
    "https://discord.gg/web3",
    "https://discord.gg/crypto",
    "https://discord.gg/nft",
]

def fallback():
    link = fallback_links[int(time.time()) % len(fallback_links)]
    send(f"⚠️ No fresh Discord found\n\n🔗 {link}")

# ---------------- MAIN SCAN ----------------

def scan_all():
    print("🔍 SCAN STARTED")

    total = 0

    total += scan_dex()
    total += scan_birdeye()

    if total == 0:
        print("No results → fallback")
        fallback()
    else:
        print(f"Total sent: {total}")

# ---------------- SCHEDULER ----------------

scheduler = BackgroundScheduler()

def start():
    print("🚀 BOT STARTED")

    send("✅ Bot is LIVE")

    scheduler.add_job(scan_all, "interval", minutes=2)
    scheduler.start()

    # First run immediately
    scan_all()

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "OK", 200

@app.route("/test")
def test():
    send("🔥 TEST OK")
    return "sent"

# ---------------- START ----------------

start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)