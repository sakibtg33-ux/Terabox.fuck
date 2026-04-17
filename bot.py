import os
import sys
import logging
import json
import asyncio
import requests
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# লগিং সেটআপ - সবকিছু কনসোলে দেখা যাবে
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# এনভায়রনমেন্ট ভেরিয়েবল চেক
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XAPIVERSE_KEY = os.environ.get("XAPIVERSE_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN environment variable is missing!")
if not XAPIVERSE_KEY:
    raise ValueError("❌ XAPIVERSE_KEY environment variable is missing!")
if not RENDER_EXTERNAL_URL:
    raise ValueError("❌ RENDER_EXTERNAL_URL environment variable is missing! (Is this a Web Service?)")

logger.info(f"✅ Using external URL: {RENDER_EXTERNAL_URL}")
logger.info(f"✅ Using port: {PORT}")

API_URL = "https://xapiverse.com/api/terabox"

# টেলিগ্রাম হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("👋 স্বাগতম! TeraBox লিংক পাঠান।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id
    logger.info(f"📨 Message from {chat_id}: {user_text}")

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
        logger.info(f"🌐 Calling API: {user_text}")
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        logger.info(f"📡 API Response Status: {response.status_code}")
        logger.info(f"📄 API Response Body (first 300 chars): {response.text[:300]}")

        # প্রসেসিং মেসেজ ডিলিট
        try:
            await processing_msg.delete()
        except Exception:
            pass

        data = response.json()

        if data.get("status") != "success" or not data.get("list"):
            await update.message.reply_text(f"❌ API error: {data.get('message', 'Unknown')}")
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
        logger.exception("🔥 Exception in handle_message")
        try:
            await processing_msg.delete()
        except:
            pass
        await update.message.reply_text("⚠️ সিস্টেম ত্রুটি, পরে চেষ্টা করুন।")

# স্বাস্থ্য পরীক্ষা হ্যান্ডলার (aiohttp)
async def health_check(request):
    return web.Response(text="Bot is alive")

async def main():
    # 1. টেলিগ্রাম অ্যাপ তৈরি
    logger.info("🚀 Initializing Telegram application...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 2. webhook সেটআপ
    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"🪝 Setting webhook to: {webhook_url}")

    # 3. লোকাল HTTP সার্ভার তৈরি (হেলথ চেক + webhook রুট)
    aiohttp_app = web.Application()
    aiohttp_app.router.add_get("/", health_check)
    aiohttp_app.router.add_post("/webhook", lambda req: app.update_queue.put(Update.de_json(await req.json(), app.bot)) or web.Response(text="ok"))

    # 4. webhook সেট করা ও সার্ভার চালু
    try:
        await app.bot.set_webhook(url=webhook_url)
        logger.info("✅ Webhook successfully set on Telegram side.")

        # 5. PTB অ্যাপ চালু (webhook মোডে)
        await app.initialize()
        await app.start()
        logger.info("✅ PTB application started.")

        # 6. লোকাল সার্ভার চালু (Render-এর জন্য)
        runner = web.AppRunner(aiohttp_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()
        logger.info(f"🌍 Local server running on 0.0.0.0:{PORT}")

        # অনির্দিষ্টকাল চালু রাখা
        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        logger.exception("💥 Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
