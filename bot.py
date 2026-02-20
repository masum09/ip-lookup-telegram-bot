import os
import time
import logging
import requests
from collections import defaultdict
from flask import Flask
from threading import Thread
import webbrowser

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# ================= SETUP MENU =================

def setup_bot():
    print("\n=== Telegram IP Lookup Bot Setup ===")
    print("1️⃣  Get BOT_TOKEN")
    print("2️⃣  Start Bot")
    print("3️⃣  Exit")

    choice = input("\nSelect option: ").strip()

    if choice == "1":
        print("\nOpening BotFather...")
        webbrowser.open("https://t.me/BotFather")
        return setup_bot()

    elif choice == "2":
        token = os.getenv("BOT_TOKEN")
        if not token:
            token = input("🔑 Enter your Telegram Bot Token: ").strip()
        return token

    else:
        print("Exiting...")
        exit()


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

# ============== Core Functions ==============

def check_rate_limit(user_id):
    now = time.time()
    if now - user_last_used[user_id] < RATE_LIMIT_SECONDS:
        return False
    user_last_used[user_id] = now
    return True

def get_ip_info(ip):
    url = f"http://ip-api.com/json/{ip}"
    response = requests.get(url, timeout=10)
    return response.json()

def format_message(ip, data):
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
"""

# ============== Handlers ==============

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

    try:
        data = get_ip_info(ip)

        if data["status"] != "success":
            await update.message.reply_text("❌ Invalid IP.")
            return

        keyboard = [
            [InlineKeyboardButton(
                "🗺 Open in Google Maps",
                url=f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
            )]
        ]

        await update.message.reply_text(
            format_message(ip, data),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(e)
        await update.message.reply_text("⚠️ Error fetching IP info.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = get_ip_info("")

    if data["status"] != "success":
        await query.edit_message_text("❌ Unable to detect IP.")
        return

    keyboard = [
        [InlineKeyboardButton(
            "🗺 Open in Google Maps",
            url=f"https://www.google.com/maps?q={data['lat']},{data['lon']}"
        )]
    ]

    await query.edit_message_text(
        format_message(data["query"], data),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

# ============== MAIN ==============

def main():
    Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ip", ip_lookup))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
