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

# এনভায়রনমেন্ট ভেরিয়েবল থেকে টোকেন ও API কী পড়া
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
XAPIVERSE_KEY = os.environ.get("XAPIVERSE_KEY")
API_URL = "https://xapiverse.com/api/terabox"

if not TELEGRAM_TOKEN or not XAPIVERSE_KEY:
    raise ValueError("TELEGRAM_TOKEN and XAPIVERSE_KEY must be set in environment variables.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """স্টার্ট কমান্ডের রেসপন্স"""
    await update.message.reply_text(
        "👋 স্বাগতম! TeraBox লিংক পাঠান, আমি ডাউনলোড লিংক দিয়ে দেব।"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """যেকোনো মেসেজ হ্যান্ডেল করা (TeraBox লিংক আশা করছি)"""
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # খুব সাধারণ লিংক চেক
    if not ("terabox.com" in user_text or "1024terabox.com" in user_text):
        await update.message.reply_text("❌ দয়া করে বৈধ TeraBox লিংক পাঠান।")
        return

    # ইউজারকে জানানো যে প্রসেসিং হচ্ছে
    processing_msg = await update.message.reply_text("⏳ লিংক প্রসেস করা হচ্ছে...")

    try:
        # API কল
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": XAPIVERSE_KEY
        }
        payload = {"url": user_text}

        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        data = response.json()

        # প্রসেসিং মেসেজ ডিলিট
        await processing_msg.delete()

        if data.get("status") != "success" or not data.get("list"):
            await update.message.reply_text("❌ ফাইল ইনফো পাওয়া যায়নি। লিংক চেক করুন।")
            return

        # প্রথম ফাইলটি নিচ্ছি (একাধিক ফাইল থাকলেও শুধু প্রথমটা)
        file_info = data["list"][0]

        # রেসপন্স মেসেজ তৈরি
        reply = f"📁 **{file_info.get('name', 'Unknown')}**\n"
        reply += f"📦 সাইজ: {file_info.get('size_formatted', 'N/A')}\n"

        if file_info.get("duration"):
            reply += f"⏱️ সময়: {file_info['duration']}\n"
        if file_info.get("quality"):
            reply += f"🎥 কোয়ালিটি: {file_info['quality']}\n"

        # ডাউনলোড লিংক
        if file_info.get("normal_dlink"):
            reply += f"\n🔗 **ডিরেক্ট ডাউনলোড:**\n`{file_info['normal_dlink']}`\n"

        # জিপ ডাউনলোড (যদি থাকে)
        if file_info.get("zip_dlink"):
            reply += f"\n📦 **জিপ ডাউনলোড:**\n`{file_info['zip_dlink']}`\n"

        # স্ট্রিমিং লিংক (M3U8)
        fast_stream = file_info.get("fast_stream_url", {})
        if fast_stream:
            stream_links = "\n".join([f"• {q}: `{url}`" for q, url in fast_stream.items()])
            reply += f"\n🎬 **স্ট্রিমিং লিংক (M3U8):**\n{stream_links}\n"

        await update.message.reply_text(reply, parse_mode="Markdown", disable_web_page_preview=True)

    except requests.exceptions.RequestException as e:
        await processing_msg.delete()
        await update.message.reply_text(f"🌐 নেটওয়ার্ক সমস্যা: {str(e)[:100]}")
    except Exception as e:
        await processing_msg.delete()
        await update.message.reply_text(f"⚠️ এরর: {str(e)[:200]}")

def main() -> None:
    """বট রান করা"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
