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
        print("First run - will send many coins with Discord from recent pairs")

def save_seen():
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen_tokens), f)
    except Exception as e:
        print(f"Error saving seen file: {e}")

def get_discord_from_profile(token_addr):
    """Fetch profile and extract Discord link if present."""
    try:
        resp = requests.get(f"https://api.dexscreener.com/token-profiles/latest/v1", timeout=10)
        if resp.status_code != 200:
            return None
        profiles = resp.json()
        for p in profiles:
            if p.get("tokenAddress") == token_addr:
                for link in p.get("links", []):
                    link_type = (link.get("type") or "").lower()
                    link_url = (link.get("url") or "").lower()
                    if link_type == "discord" or "discord.gg" in link_url or "discord.com/invite" in link_url:
                        return link.get("url")
        return None
    except:
        return None

def scan_coins(initial=False):
    global seen_tokens
    try:
        # 1. Get recent new pairs (much higher volume than profiles only)
        chains = ["solana", "base", "ethereum", "bsc"]  # Add more if wanted
        sent_count = 0

        for chain in chains:
            # New pairs endpoint gives recently created trading pairs
            url = f"https://api.dexscreener.com/latest/dex/pairs/{chain}"
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            pairs = data.get("pairs", [])[:100]  # Limit to avoid too many calls

            for pair in pairs:
                token_addr = pair.get("baseToken", {}).get("address") or pair.get("quoteToken", {}).get("address")
                if not token_addr or token_addr in seen_tokens:
                    continue

                # Check for Discord via profile
                discord_link = get_discord_from_profile(token_addr)
                if not discord_link:
                    continue  # Only send if Discord exists

                seen_tokens.add(token_addr)
                save_seen()

                name = pair.get("baseToken", {}).get("name") or "Unknown"
                dex_url = pair.get("url") or f"https://dexscreener.com/{chain}/{pair.get('pairAddress')}"
                desc = pair.get("baseToken", {}).get("symbol") or "No description"

                message = (
                    f"🪙 New Coin with Discord (from recent pairs)\n\n"
                    f"Name: {name}\n"
                    f"Token Address: {token_addr}\n"
                    f"Discord: {discord_link}\n"
                    f"DexScreener: {dex_url}\n"
                    f"Chain: {chain.upper()}\n\n"
                    f"Only Discord links • Scans every 5 min"
                )
                bot.send_message(USER_CHAT_ID, message)
                print(f"✅ Sent: {token_addr} ({name}) on {chain}")
                sent_count += 1

        # Also run a quick profile scan for extra coverage
        try:
            resp = requests.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=10)
            if resp.status_code == 200:
                for profile in resp.json():
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
                        save_seen()
                        # Similar message construction...
                        name = profile.get("name") or "Unknown"
                        dex_url = profile.get("url") or f"https://dexscreener.com/solana/{token_addr}"
                        message = f"🪙 New Coin with Discord\nName: {name}\nToken: {token_addr}\nDiscord: {discord_link}\nDexScreener: {dex_url}\n\nOnly Discord"
                        bot.send_message(USER_CHAT_ID, message)
                        print(f"✅ Sent profile coin: {token_addr}")
                        sent_count += 1
        except:
            pass

        if sent_count > 0:
            print(f"Sent {sent_count} new Discord coin(s) this scan")
        else:
            print("No new Discord coins found in this scan cycle")

    except Exception as e:
        print(f"Scan error: {e}")

@app.route('/')
def home():
    return "✅ Enhanced Coin Discord Scanner is RUNNING! (new pairs + profiles for more coins)"

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scan_coins, 'interval', minutes=5, id='discord_scan', args=[False])
    scheduler.start()
    print("🕒 Scheduler started – scanning new pairs every 5 minutes")

    # Heavy initial scan on startup for maximum coins (≈ recent 2 weeks activity)
    print("Starting big initial scan for many coins...")
    for i in range(6):   # Multiple rounds to catch more
        print(f"Initial round {i+1}/6")
        scan_coins(initial=True)
        time.sleep(10)   # Give API time to return fresh data

    print("Initial batch done. Now normal scanning.")

if __name__ == "__main__":
    load_seen()
    thread = threading.Thread(target=start_scheduler, daemon=True)
    thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)