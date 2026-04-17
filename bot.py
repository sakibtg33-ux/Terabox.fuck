import os
import sys
import logging
import json
import asyncio
import requests
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# লগিং সেটআপ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# এনভায়রনমেন্ট ভেরিয়েবল
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XAPIVERSE_KEY = os.environ.get("XAPIVERSE_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN missing")
if not XAPIVERSE_KEY:
    raise ValueError("❌ XAPIVERSE_KEY missing")
if not RENDER_EXTERNAL_URL:
    raise ValueError("❌ RENDER_EXTERNAL_URL missing")

logger.info(f"External URL: {RENDER_EXTERNAL_URL}")
logger.info(f"Port: {PORT}")

API_URL = "https://xapiverse.com/api/terabox"

# Telegram হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 TeraBox লিংক পাঠান।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id
    logger.info(f"Message from {chat_id}: {user_text}")

    if not ("terabox.com" in user_text or "1024terabox.com" in user_text):
        await update.message.reply_text("❌ বৈধ TeraBox লিংক দিন।")
        return

    processing_msg = await update.message.reply_text("⏳ প্রসেসিং...")

    try:
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": user_text}
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        logger.info(f"API status: {response.status_code}")

        try:
            await processing_msg.delete()
        except:
            pass

        data = response.json()
        if data.get("status") != "success" or not data.get("list"):
            await update.message.reply_text(f"❌ API Error: {data.get('message', 'Unknown')}")
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
        logger.exception("Error in handle_message")
        try:
            await processing_msg.delete()
        except:
            pass
        await update.message.reply_text("⚠️ সিস্টেম ত্রুটি, পরে চেষ্টা করুন।")

# Webhook রিকোয়েস্ট হ্যান্ডলার (aiohttp এর জন্য)
async def webhook_handler(request):
    app = request.app['telegram_app']  # আমরা app অবজেক্ট স্টোর করেছি
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.update_queue.put(update)
    return web.Response(text="ok")

# স্বাস্থ্য পরীক্ষা
async def health_check(request):
    return web.Response(text="Bot is running")

async def main():
    # 1. PTB Application তৈরি
    logger.info("Initializing PTB Application...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 2. Webhook URL সেট
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"Setting webhook: {webhook_url}")
    await app.bot.set_webhook(url=webhook_url)

    # 3. PTB Application শুরু
    await app.initialize()
    await app.start()
    logger.info("PTB Application started.")

    # 4. aiohttp ওয়েব সার্ভার তৈরি
    aiohttp_app = web.Application()
    aiohttp_app['telegram_app'] = app  # webhook_handler এ ব্যবহারের জন্য
    aiohttp_app.router.add_get("/", health_check)
    aiohttp_app.router.add_post("/webhook", webhook_handler)

    # 5. সার্ভার চালু
    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Server running on port {PORT}")

    # চিরতরে চলতে থাকা
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
