import os
import logging
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# লগিং কনফিগার
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
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
    chat_id = update.effective_chat.id

    logger.info(f"Received message from {chat_id}: {user_text}")

    if not ("terabox.com" in user_text or "1024terabox.com" in user_text):
        await update.message.reply_text("❌ দয়া করে বৈধ TeraBox লিংক পাঠান।")
        return

    processing_msg = await update.message.reply_text("⏳ লিংক প্রসেস করা হচ্ছে...")
    logger.info("Sent processing message")

    try:
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": user_text}
        logger.info(f"Calling API with URL: {user_text}")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        logger.info(f"API response status: {response.status_code}")
        # কনসোলে পুরো রেসপন্স প্রিন্ট করি (প্রথম 500 অক্ষর)
        logger.info(f"API response body: {response.text[:500]}")

        # প্রসেসিং মেসেজ ডিলিটের চেষ্টা
        try:
            await processing_msg.delete()
        except Exception as del_err:
            logger.warning(f"Could not delete processing message: {del_err}")

        # রেসপন্স পার্স
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error("Response is not valid JSON")
            await update.message.reply_text("❌ API থেকে ভুল ফরম্যাটে ডাটা এসেছে।")
            return

        # চেক করি API success কিনা
        if data.get("status") != "success":
            error_msg = data.get("message", "Unknown error")
            logger.error(f"API returned error: {error_msg}")
            await update.message.reply_text(f"❌ API এরর: {error_msg}")
            return

        if not data.get("list") or len(data["list"]) == 0:
            logger.error("API returned success but list is empty")
            await update.message.reply_text("❌ ফাইল ইনফো পাওয়া যায়নি।")
            return

        # প্রথম ফাইল ইনফো
        file_info = data["list"][0]
        logger.info(f"File info: {file_info}")

        # মেসেজ তৈরি
        name = file_info.get('name', 'Unknown')
        size = file_info.get('size_formatted', 'N/A')
        duration = file_info.get('duration', '')
        quality = file_info.get('quality', '')
        normal_link = file_info.get('normal_dlink', '')
        zip_link = file_info.get('zip_dlink', '')

        reply = f"📁 **{name}**\n"
        reply += f"📦 সাইজ: {size}\n"
        if duration:
            reply += f"⏱️ সময়: {duration}\n"
        if quality:
            reply += f"🎥 কোয়ালিটি: {quality}\n"
        if normal_link:
            reply += f"\n🔗 **ডিরেক্ট ডাউনলোড:**\n`{normal_link}`\n"
        if zip_link:
            reply += f"\n📦 **জিপ ডাউনলোড:**\n`{zip_link}`\n"

        logger.info(f"Sending reply to {chat_id}")
        await update.message.reply_text(
            reply,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info("Reply sent successfully")

    except Exception as e:
        logger.exception("Unhandled exception in handle_message")
        # প্রসেসিং মেসেজ ডিলিট চেষ্টা
        try:
            await processing_msg.delete()
        except:
            pass
        # ইউজারকে এরর জানানো
        try:
            await update.message.reply_text(f"⚠️ সিস্টেম এরর হয়েছে। অনুগ্রহ করে পরে চেষ্টা করুন।")
        except Exception as send_err:
            logger.error(f"Even error message could not be sent: {send_err}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"Setting webhook to {webhook_url}")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=webhook_url,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
