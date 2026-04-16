import os
import logging
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# লগিং সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask অ্যাপ তৈরি (Render-এর প্রয়োজন)
flask_app = Flask(__name__)

# এনভায়রনমেন্ট ভেরিয়েবল
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XAPIVERSE_KEY = os.environ.get("XAPIVERSE_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")  # Render অটোমেটিক দেয়
API_URL = "https://xapiverse.com/api/terabox"

if not TELEGRAM_TOKEN or not XAPIVERSE_KEY:
    raise ValueError("TELEGRAM_TOKEN and XAPIVERSE_KEY must be set.")

# Telegram Bot Application
app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 স্বাগতম! TeraBox লিংক পাঠান, আমি ডাউনলোড লিংক দিয়ে দেব।"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not ("terabox.com" in user_text or "1024terabox.com" in user_text):
        await update.message.reply_text("❌ দয়া করে বৈধ TeraBox লিংক পাঠান।")
        return

    processing_msg = await update.message.reply_text("⏳ লিংক প্রসেস করা হচ্ছে...")

    try:
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": user_text}
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        data = response.json()
        await processing_msg.delete()

        if data.get("status") != "success" or not data.get("list"):
            await update.message.reply_text("❌ ফাইল ইনফো পাওয়া যায়নি। লিংক চেক করুন।")
            return

        file_info = data["list"][0]
        reply = f"📁 **{file_info.get('name', 'Unknown')}**\n"
        reply += f"📦 সাইজ: {file_info.get('size_formatted', 'N/A')}\n"
        if file_info.get("duration"):
            reply += f"⏱️ সময়: {file_info['duration']}\n"
        if file_info.get("quality"):
            reply += f"🎥 কোয়ালিটি: {file_info['quality']}\n"
        if file_info.get("normal_dlink"):
            reply += f"\n🔗 **ডিরেক্ট ডাউনলোড:**\n`{file_info['normal_dlink']}`\n"
        if file_info.get("zip_dlink"):
            reply += f"\n📦 **জিপ ডাউনলোড:**\n`{file_info['zip_dlink']}`\n"

        await update.message.reply_text(reply, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        await processing_msg.delete()
        await update.message.reply_text(f"⚠️ এরর: {str(e)[:200]}")

# Flask রুট - Render হেলথ চেক
@flask_app.route('/')
def home():
    return "Bot is running!"

# Webhook রুট
@flask_app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), app.bot)
        app.update_queue.put(update)
        return "ok"

# Webhook সেটআপ
async def setup_webhook():
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    await app.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

# হ্যান্ডলার রেজিস্টার
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    import asyncio
    # প্রথমে webhook সেট করো
    asyncio.run(setup_webhook())
    # Flask সার্ভার চালু করো (Render 0.0.0.0:10000 তে শোনে)
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
