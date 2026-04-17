import os
import sys
import logging
import asyncio
import re
import requests
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)

# ================== কনফিগ ==================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ENV_XAPIVERSE_KEY = os.environ.get("XAPIVERSE_KEY")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))
ADMIN_USER_ID = 6552783238  # ← এখানে তোমার টেলিগ্রাম ইউজার আইডি বসাও!

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN missing")
if not ENV_XAPIVERSE_KEY:
    raise ValueError("❌ XAPIVERSE_KEY missing")
if not RENDER_EXTERNAL_URL:
    raise ValueError("❌ RENDER_EXTERNAL_URL missing")

API_URL = "https://xapiverse.com/api/terabox"

# মেমোরিতে সংরক্ষিত API কী
current_api_key = None

def get_api_key() -> str:
    return current_api_key if current_api_key else ENV_XAPIVERSE_KEY

# ================== TeraBox ডোমেইন তালিকা ==================
TERABOX_DOMAINS = [
    "1024terabox.com", "terabox.com", "terabox.app", "1024tera.com",
    "teraboxshare.com", "teraboxlink.com", "terasharelink.com", "terabox.club",
    "mirrobox.com", "4funbox.com", "nephobox.com", "tibibox.com",
    "momerybox.com", "terafileshare.com", "terasharefile.com"
]

def extract_terabox_link(text: str):
    domain_pattern = "|".join(TERABOX_DOMAINS)
    pattern = rf'https?://(?:[\w-]+\.)?(?:{domain_pattern})/\S+'
    match = re.search(pattern, text)
    return match.group(0) if match else None

# ================== API কল ==================
def fetch_file_info(url: str):
    try:
        headers = {
            "Content-Type": "application/json",
            "xAPIverse-Key": get_api_key()
        }
        payload = {"url": url}
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"API non-200 for {url}: {resp.status_code}")
            return None
        data = resp.json()
        if data.get("status") != "success" or not data.get("list"):
            logger.error(f"API error for {url}: {data.get('message')}")
            return None
        return data["list"][0]
    except Exception as e:
        logger.exception(f"API exception for {url}")
        return None

# ================== ইনলাইন কীবোর্ড ==================
def build_main_keyboard(file_info: dict):
    normal = file_info.get("normal_dlink", "")
    zip_link = file_info.get("zip_dlink", "")
    streams = file_info.get("fast_stream_url", {})

    buttons = []
    if normal or streams:
        buttons.append(InlineKeyboardButton("📥 ডাউনলোড", callback_data="dl_menu"))
    if zip_link:
        buttons.append(InlineKeyboardButton("📦 জিপ", callback_data="zip_show"))
    if streams:
        buttons.append(InlineKeyboardButton("🎬 স্ট্রিম", callback_data="stream_menu"))

    return InlineKeyboardMarkup([buttons]) if buttons else None

# ================== টেলিগ্রাম হ্যান্ডলার ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 TeraBox লিংক পাঠান (একটি করে)।\n\n"
        "⚙️ অ্যাডমিন: /setkey <api_key>"
    )

async def set_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ আপনি অ্যাডমিন নন।")
        return

    if not context.args:
        await update.message.reply_text("❗ ব্যবহার: /setkey <নতুন_api_key>")
        return

    global current_api_key
    new_key = context.args[0].strip()
    current_api_key = new_key
    logger.info(f"Admin {user_id} changed API key to: {new_key[:10]}...")
    await update.message.reply_text("✅ API কী আপডেট হয়েছে (মেমোরিতে)।")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    link = extract_terabox_link(user_text)

    if not link:
        await update.message.reply_text("❌ কোনো বৈধ TeraBox লিংক পাওয়া যায়নি।")
        return

    status_msg = await update.message.reply_text("⏳ প্রসেস করা হচ্ছে...")

    file_info = fetch_file_info(link)

    try:
        await status_msg.delete()
    except:
        pass

    if not file_info:
        await update.message.reply_text("❌ ফাইল ইনফো পাওয়া যায়নি। লিংক চেক করুন অথবা API ক্রেডিট শেষ কিনা দেখুন।")
        return

    context.user_data["last_file"] = file_info

    name = file_info.get('name', 'Unknown').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    size = file_info.get('size_formatted', 'N/A')
    text = f"📁 <b>{name}</b>\n📦 {size}"
    if file_info.get("duration"):
        text += f"\n⏱️ {file_info['duration']}"
    if file_info.get("quality"):
        text += f"\n🎥 {file_info['quality']}"

    reply_markup = build_main_keyboard(file_info)

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=reply_markup
    )

# ================== ক্যালব্যাক হ্যান্ডলার ==================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data:
        return

    file_info = context.user_data.get("last_file")
    if not file_info:
        await query.edit_message_text("⏳ সেশন শেষ। আবার লিংক পাঠান।")
        return

    # ---------- মূল মেনুতে ফেরা ----------
    if data == "back_to_main":
        name = file_info.get('name', 'Unknown').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        size = file_info.get('size_formatted', 'N/A')
        text = f"📁 <b>{name}</b>\n📦 {size}"
        if file_info.get("duration"):
            text += f"\n⏱️ {file_info['duration']}"
        if file_info.get("quality"):
            text += f"\n🎥 {file_info['quality']}"
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=build_main_keyboard(file_info))
        return

    # ---------- জিপ লিংক দেখানো ----------
    if data == "zip_show":
        link = file_info.get("zip_dlink")
        if link:
            await query.edit_message_text(
                f"📁 {file_info.get('name', 'Unknown')}\n\n📦 <code>{link}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="back_to_main")]])
            )
        else:
            await query.edit_message_text("❌ জিপ লিংক নেই।")
        return

    # ---------- স্ট্রিম মেনু ----------
    if data == "stream_menu":
        streams = file_info.get("fast_stream_url", {})
        if not streams:
            await query.edit_message_text("❌ স্ট্রিমিং লিংক নেই।")
            return
        keyboard = []
        for quality in streams.keys():
            keyboard.append([InlineKeyboardButton(f"🎬 {quality}", callback_data=f"stream_play_{quality}")])
        keyboard.append([InlineKeyboardButton("🔙 ফিরুন", callback_data="back_to_main")])
        await query.edit_message_text(
            f"🎬 স্ট্রিম কোয়ালিটি বাছুন:\n📁 {file_info.get('name', 'Unknown')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # ---------- স্ট্রিম প্লে ----------
    if data.startswith("stream_play_"):
        quality = data.replace("stream_play_", "")
        streams = file_info.get("fast_stream_url", {})
        url = streams.get(quality)
        if url:
            await query.edit_message_text(
                f"🎬 {quality} স্ট্রিম (M3U8):\n\n<code>{url}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="back_to_main")]])
            )
        else:
            await query.answer("সেই কোয়ালিটি নেই।")
        return

    # ---------- ডাউনলোড মেনু (নতুন) ----------
    if data == "dl_menu":
        name = file_info.get('name', 'Unknown')
        keyboard = []

        # সরাসরি ডাউনলোড (normal_dlink)
        if file_info.get("normal_dlink"):
            keyboard.append([InlineKeyboardButton("📥 সরাসরি ডাউনলোড (MP4/MKV)", callback_data="dl_direct")])

        # M3U8 স্ট্রিম ডাউনলোড
        streams = file_info.get("fast_stream_url", {})
        if streams:
            for quality in streams.keys():
                keyboard.append([InlineKeyboardButton(f"🎬 {quality} স্ট্রিম (M3U8)", callback_data=f"dl_m3u8_{quality}")])

        keyboard.append([InlineKeyboardButton("🔙 ফিরুন", callback_data="back_to_main")])

        await query.edit_message_text(
            f"📥 ডাউনলোড / স্ট্রিম অপশন:\n📁 {name}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # সরাসরি ডাউনলোড
    if data == "dl_direct":
        link = file_info.get("normal_dlink")
        if link:
            await query.edit_message_text(
                f"📥 সরাসরি ডাউনলোড লিংক:\n\n<code>{link}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="back_to_main")]])
            )
        else:
            await query.answer("❌ সরাসরি ডাউনলোড লিংক নেই।")
        return

    # M3U8 স্ট্রিম ডাউনলোড
    if data.startswith("dl_m3u8_"):
        quality = data.replace("dl_m3u8_", "")
        streams = file_info.get("fast_stream_url", {})
        url = streams.get(quality)
        if url:
            await query.edit_message_text(
                f"🎬 {quality} স্ট্রিম (M3U8):\n\n<code>{url}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ফিরুন", callback_data="back_to_main")]])
            )
        else:
            await query.answer("সেই কোয়ালিটি নেই।")
        return

# ================== ওয়েবহুক ও সার্ভার ==================
async def webhook_handler(request):
    app = request.app['telegram_app']
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.update_queue.put(update)
    return web.Response(text="ok")

async def health_check(request):
    return web.Response(text="Bot is running")

async def main():
    logger.info("Initializing PTB Application...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setkey", set_key))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    logger.info(f"Setting webhook: {webhook_url}")
    await app.bot.set_webhook(url=webhook_url)

    await app.initialize()
    await app.start()
    logger.info("PTB Application started.")

    aiohttp_app = web.Application()
    aiohttp_app['telegram_app'] = app
    aiohttp_app.router.add_get("/", health_check)
    aiohttp_app.router.add_post("/webhook", webhook_handler)

    runner = web.AppRunner(aiohttp_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Server running on port {PORT}")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
