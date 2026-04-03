import os
import threading
import time
import requests
from flask import Flask
import telebot
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# CONFIG FROM RENDER ENVIRONMENT VARIABLES
BOT_TOKEN = os.environ.get('BOT_TOKEN')
USER_CHAT_ID = int(os.environ.get('USER_CHAT_ID', 5578314612))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

bot = telebot.TeleBot(BOT_TOKEN)
seen_tokens = set()  # Prevents duplicate messages

def scan_coins():
    """Scan latest DexScreener token profiles for Discord links only."""
    global seen_tokens
    try:
        # Free public DexScreener API - latest token profiles
        resp = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=15)
        resp.raise_for_status()
        profiles = resp.json()

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

    except Exception as e:
        print(f"Scan error: {e}")

@app.route('/')
def home():
    return "Coin Discord Scanner Bot is RUNNING on Render! Scanning every 5 minutes for new coins with Discord links only."

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_coins, 'interval', minutes=5, id='discord_scan')
    scheduler.start()
    print("Scheduler started - scanning for coins with Discord every 5 minutes")
    # Run once immediately on startup
    time.sleep(5)
    scan_coins()

if __name__ == "__main__":
    # Start scanner in background thread
    thread = threading.Thread(target=start_scheduler, daemon=True)
    thread.start()

    # Render requires a web server
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)