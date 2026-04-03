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

bot = telebot.TeleBot(BOT_TOKEN)

SEEN_FILE = "seen_tokens.json"
seen_tokens = set()

# ---------------- LOAD ----------------

def load_seen():
    global seen_tokens
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen_tokens = set(json.load(f))
        except:
            seen_tokens = set()

def save_seen():
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_tokens), f)

# ---------------- DISCORD ----------------

def extract_discord(text):
    if not text:
        return None

    text = str(text).lower()

    if "discord.gg" in text or "discord.com/invite" in text:
        words = text.split()
        for w in words:
            if "discord" in w:
                return w
    return None

# ---------------- BIRDEYE (SOLANA 🔥) ----------------

def scan_birdeye():
    print("Scanning Birdeye...")
    try:
        url = "https://public-api.birdeye.so/defi/tokenlist?sort_by=v24hUSD&sort_type=desc&offset=0&limit=50"

        headers = {
            "accept": "application/json",
            "x-chain": "solana"
        }

        r = requests.get(url, headers=headers, timeout=15)

        if r.status_code != 200:
            return

        tokens = r.json().get("data", {}).get("tokens", [])

        for t in tokens:
            addr = t.get("address")

            if not addr or addr in seen_tokens:
                continue

            desc = str(t)

            discord = extract_discord(desc)
            if not discord:
                continue

            seen_tokens.add(addr)
            save_seen()

            name = t.get("symbol", "SOL TOKEN")

            msg = (
                f"🔥 SOLANA TOKEN (BIRDEYE)\n\n"
                f"{name}\n\n"
                f"🔗 {discord}\n"
                f"https://birdeye.so/token/{addr}"
            )

            bot.send_message(USER_CHAT_ID, msg)
            print("Sent Birdeye:", name)

    except Exception as e:
        print("Birdeye error:", e)

# ---------------- RAYDIUM ----------------

def scan_raydium():
    print("Scanning Raydium...")
    try:
        url = "https://api.raydium.io/v2/main/pairs"

        r = requests.get(url, timeout=15)

        if r.status_code != 200:
            return

        pairs = r.json()[:50]

        for p in pairs:
            addr = p.get("baseMint")

            if not addr or addr in seen_tokens:
                continue

            desc = str(p)

            discord = extract_discord(desc)
            if not discord:
                continue

            seen_tokens.add(addr)
            save_seen()

            name = p.get("name", "Raydium Token")

            msg = (
                f"⚡ RAYDIUM NEW PAIR\n\n"
                f"{name}\n\n"
                f"🔗 {discord}\n"
                f"https://raydium.io/swap/?inputCurrency=sol&outputCurrency={addr}"
            )

            bot.send_message(USER_CHAT_ID, msg)
            print("Sent Raydium:", name)

    except Exception as e:
        print("Raydium error:", e)

# ---------------- DEXSCREENER ----------------

def scan_dex():
    print("Scanning Dex...")
    chains = ["solana", "ethereum", "bsc", "base"]

    for chain in chains:
        try:
            url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}"
            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                continue

            pairs = r.json().get("pairs", [])[:50]

            for pair in pairs:
                base = pair.get("baseToken", {})
                addr = base.get("address")

                if not addr or addr in seen_tokens:
                    continue

                desc = str(pair)

                discord = extract_discord(desc)
                if not discord:
                    continue

                seen_tokens.add(addr)
                save_seen()

                name = base.get("symbol", "TOKEN")

                msg = (
                    f"🚀 DEX COIN\n\n"
                    f"{name} ({chain})\n\n"
                    f"🔗 {discord}\n"
                    f"{pair.get('url')}"
                )

                bot.send_message(USER_CHAT_ID, msg)
                print("Sent Dex:", name)

        except Exception as e:
            print("Dex error:", e)

# ---------------- MAIN SCAN ----------------

def scan_all():
    scan_birdeye()
    scan_raydium()
    scan_dex()

# ---------------- START ----------------

def start():
    bot.send_message(USER_CHAT_ID, "✅ Bot started (Multi-source scanning)")

    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_all, "interval", minutes=3)
    scheduler.start()

    # FORCE FIRST RESULTS
    for i in range(3):
        print(f"Initial scan {i+1}")
        scan_all()
        time.sleep(5)

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return "OK", 200

@app.route("/test")
def test():
    bot.send_message(USER_CHAT_ID, "🔥 Test message working")
    return "sent"

# ---------------- MAIN ----------------

if __name__ == "__main__":
    load_seen()
    threading.Thread(target=start, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)