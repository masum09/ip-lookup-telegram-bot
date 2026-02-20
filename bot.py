import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

# যদি .env না থাকে তাহলে prompt দেখাবে
if not BOT_TOKEN:
    BOT_TOKEN = input("🔑 Enter your Telegram Bot Token: ").strip()

if not API_KEY:
    API_KEY = input("🌍 Enter your API Ninjas API Key: ").strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me an IP address and I will return its location info!"
    )


async def lookup_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip = update.message.text.strip()

    url = f"https://api.api-ninjas.com/v1/iplookup?address={ip}"
    headers = {"X-Api-Key": API_KEY}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        if not data:
            await update.message.reply_text("❌ No data found for this IP.")
            return

        message = (
            f"🌍 IP: {data.get('ip')}\n"
            f"🏳 Country: {data.get('country')}\n"
            f"📍 Region: {data.get('region')}\n"
            f"🏙 City: {data.get('city')}\n"
            f"📡 ISP: {data.get('isp')}\n"
            f"📌 Latitude: {data.get('latitude')}\n"
            f"📌 Longitude: {data.get('longitude')}"
        )

        await update.message.reply_text(message)
    else:
        await update.message.reply_text("❌ Invalid IP or API Error!")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lookup_ip))

    print("🚀 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
