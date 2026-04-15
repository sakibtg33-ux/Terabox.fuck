import logging
import json
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# ===== CONFIG =====
BOT_TOKEN = "YOUR_BOT_TOKEN"
API_KEY = "YOUR_API_KEY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)


# ===== BEST QUALITY =====
def get_best(file):
    streams = file.get("fast_stream_url", {})
    if streams:
        return list(streams.values())[-1]  # highest quality
    return file.get("normal_dlink")


# ===== START =====
@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    await msg.reply("👋 Send Terabox link")


# ===== MAIN =====
@dp.message_handler()
async def main(msg: types.Message):
    text = msg.text

    if "terabox" not in text:
        return await msg.reply("❌ Send valid Terabox link")

    await msg.reply("⏳ Processing...")

    try:
        # link fix
        url = text
        if "teraboxshare.com" in text:
            url = text.replace("teraboxshare.com", "1024terabox.com")

        # API call
        res = requests.post(
            "https://xapiverse.com/api/terabox",
            json={"url": url},
            headers={
                "Content-Type": "application/json",
                "xAPIverse-Key": API_KEY
            },
            timeout=15
        )

        data = res.json()
        files = data.get("list", [])

        if not files:
            return await msg.reply("❌ No file found")

        # ===== BUTTON UI =====
        kb = InlineKeyboardMarkup(row_width=1)

        for file in files[:10]:
            best = get_best(file)

            kb.add(
                InlineKeyboardButton(
                    text=f"{file.get('name')} ({file.get('size_formatted')})",
                    callback_data=json.dumps({
                        "name": file.get("name"),
                        "size": file.get("size_formatted"),
                        "url": best
                    })
                )
            )

        await msg.reply("📂 Select file 👇", reply_markup=kb)

    except Exception as e:
        await msg.reply(f"❌ Error:\n{str(e)}")


# ===== BUTTON CLICK =====
@dp.callback_query_handler()
async def click(call: types.CallbackQuery):
    data = json.loads(call.data)

    msg = (
        f"🎥 {data['name']}\n"
        f"📦 {data['size']}\n\n"
        f"⬇️ Best Quality:\n{data['url']}"
    )

    await call.message.reply(msg)
    await call.answer()


# ===== RUN =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
