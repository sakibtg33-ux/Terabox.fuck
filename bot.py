import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# লগিং সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# এনভায়রনমেন্ট ভেরিয়েবল
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XAPIVERSE_KEY = os.environ.get("XAPIVERSE_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TELEGRAM_TOKEN or not XAPIVERSE_KEY:
    raise ValueError("TELEGRAM_TOKEN and XAPIVERSE_KEY must be set.")

API_URL = "https://xapiverse.com/api/terabox"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 স্বাগতম! TeraBox লিংক পাঠান, আমি ডাউনলোড লিংক দিয়ে দেব।"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text.strip()

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

def main():
    # অ্যাপ্লিকেশন তৈরি
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # হ্যান্ডলার রেজিস্টার
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook URL
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"Setting webhook to {webhook_url}")

    # Webhook সার্ভার চালু (Render-এ HTTP পোর্ট 0.0.0.0:PORT)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",          # টেলিগ্রাম যেখানে পোস্ট করবে
        webhook_url=webhook_url,
        drop_pending_updates=True    # পূর্বের জমে থাকা আপডেট বাদ দাও
    )

if __name__ == "__main__":
    main()
