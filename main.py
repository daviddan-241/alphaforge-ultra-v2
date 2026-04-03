import os
import threading
import time
import json
import requests
from flask import Flask
import telebot
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# CONFIG FROM RENDER ENVIRONMENT VARIABLES
BOT_TOKEN = os.environ.get('BOT_TOKEN')
USER_CHAT_ID = int(os.environ.get('USER_CHAT_ID', 5578314612))
SEEN_FILE = "seen_tokens.json"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

bot = telebot.TeleBot(BOT_TOKEN)
seen_tokens = set()

def load_seen():
    global seen_tokens
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                seen_tokens = set(json.load(f))
            print(f"Loaded {len(seen_tokens)} previously seen tokens")
        except Exception as e:
            print(f"Error loading seen file: {e}")
            seen_tokens = set()
    else:
        seen_tokens = set()
        print("No seen file yet - first run will send all current Discord coins")

def save_seen():
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_tokens), f)
    except Exception as e:
        print(f"Error saving seen file: {e}")

def scan_coins():
    """Scan latest DexScreener token profiles for Discord links only."""
    global seen_tokens
    try:
        resp = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15)
        resp.raise_for_status()
        profiles = resp.json()

        new_sent = 0
        for profile in profiles:
            token_addr = profile.get("tokenAddress")
            if not token_addr or token_addr in seen_tokens:
                continue

            discord_link = None
            for link in profile.get("links", []):
                link_type = (link.get("type") or "").lower()
                link_url = (link.get("url") or "").lower()
                if link_type == "discord" or "discord.gg" in link_url or "discord.com/invite" in link_url:
                    discord_link = link.get("url")
                    break

            if discord_link:
                seen_tokens.add(token_addr)
                save_seen()  # persist immediately
                chain = profile.get("chainId", "solana")
                dex_url = profile.get("url") or f"https://dexscreener.com/{chain}/{token_addr}"
                desc = (profile.get("description") or "No description")[:300]

                message = (
                    f"New Coin with Discord (recent profile)\n\n"
                    f"Token Address: {token_addr}\n"
                    f"Discord: {discord_link}\n"
                    f"DexScreener: {dex_url}\n"
                    f"Description: {desc}\n\n"
                    f"Only coins with Discord links. Scans every 5 min."
                )
                bot.send_message(USER_CHAT_ID, message)
                print(f"Sent Discord for {token_addr}")
                new_sent += 1

        if new_sent == 0:
            print("No new Discord coins in this scan")
        else:
            print(f"Sent {new_sent} new Discord coin(s)")

    except Exception as e:
        print(f"Scan error: {e}")

@app.route('/')
def home():
    return "✅ Coin Discord Scanner Bot is RUNNING on Render! (scanning every 5 min)"

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_coins, 'interval', minutes=5, id='discord_scan')
    scheduler.start()
    print("🕒 Scheduler started – scanning every 5 minutes")
    # First run immediately (this sends the "everything from last ~2 weeks" batch)
    time.sleep(3)
    scan_coins()

if __name__ == "__main__":
    load_seen()                    # load previously seen coins
    thread = threading.Thread(target=start_scheduler, daemon=True)
    thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)