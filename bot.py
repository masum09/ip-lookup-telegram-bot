import os
import time
import logging
import requests
from collections import defaultdict
from flask import Flask
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= SETUP MENU =================

def setup_bot():
    while True:
        print("\n=== Telegram IP Lookup Bot Setup ===")
        print("1️⃣  Get BOT_TOKEN")
        print("2️⃣  Start Bot")
        print("3️⃣  Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            token = input("\n🔑 Paste your Telegram BOT_TOKEN here:\n> ").strip()
            if token:
                print("\n✅ BOT_TOKEN saved temporarily for this session.")
                return token
            else:
                print("❌ Invalid token. Try again.")

        elif choice == "2":
            token = os.getenv("BOT_TOKEN")
            if token:
                print("✅ Using BOT_TOKEN from environment.")
                return token
            else:
                print("❌ No BOT_TOKEN found in environment.")
                print("Please select option 1 to enter manually.")

        elif choice == "3":
            print("Exiting...")
            exit()

        else:
            print("❌ Invalid option. Try again.")

# ================= CONFIG =================

BOT_TOKEN = setup_bot()
PORT = int(os.environ.get("PORT", 8080))
RATE_LIMIT_SECONDS = 10
user_last_used = defaultdict(int)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== Flask Keep Alive (Hosting Ready) ==============

app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app_flask.run(host='0.0.0.0', port=PORT)

# ============== Core Functions =================

def check_rate_limit(user_id):
    now = time.time()
    if now - user_last_used[user_id] < RATE_LIMIT_SECONDS:
        return False
    user_last_used[user_id] = now
    return True

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org", timeout=10)
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting public IP: {e}")
        return None

def get_ip_info(ip):
    try:
        url = f"http://ip-api.com/json/{ip}"
        response = requests.get(url, timeout=30)
        data = response.json()
        logger.info(f"API Response: {data}")  # Debug log
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Requests Exception: {e}")
        return {"status": "fail", "message": str(e)}

def format_message(ip, data):
    maps_link = f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}"
    return f"""
🌐 *IP Address:* `{ip}`

🌍 *Country:* {data.get('country')}
📍 *Region:* {data.get('regionName')}
🏙 *City:* {data.get('city')}

📡 *ISP:* {data.get('isp')}
🏢 *Organization:* {data.get('org')}
🛰 *ASN:* {data.get('as')}

🕒 *Timezone:* {data.get('timezone')}

📌 *Coordinates:* `{data.get('lat')}, {data.get('lon')}`
🗺 [Open in Google Maps]({maps_link})
"""

# ============== Handlers =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌍 Lookup My IP", callback_data="myip")]
    ]
    await update.message.reply_text(
        "🚀 *Advanced IP Lookup Bot*\n\n"
        "Use command:\n"
        "`/ip 8.8.8.8`\n\n"
        "Or press button 👇",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ip_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳ Please wait before using again.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /ip 8.8.8.8")
        return

    ip = context.args[0]
    data = get_ip_info(ip)

    if data.get("status") != "success":
        await update.message.reply_text(f"⚠️ Failed to fetch IP info.\nMessage: {data.get('message', 'Unknown error')}")
        return

    keyboard = [
        [InlineKeyboardButton("🗺 Open in Google Maps", url=f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}")]
    ]

    await update.message.reply_text(
        format_message(ip, data),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    public_ip = get_public_ip()
    if not public_ip:
        await query.edit_message_text("⚠️ Unable to detect your public IP.")
        return

    data = get_ip_info(public_ip)
    if data.get("status") != "success":
        await query.edit_message_text(f"⚠️ Failed to fetch IP info.\nMessage: {data.get('message', 'Unknown error')}")
        return

    keyboard = [
        [InlineKeyboardButton("🗺 Open in Google Maps", url=f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}")]
    ]

    await query.edit_message_text(
        format_message(public_ip, data),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

# ============== MAIN =================

def main():
    Thread(target=run_flask).start()  # Hosting keep-alive

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ip", ip_lookup))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
