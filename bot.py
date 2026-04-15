import asyncio
import json
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ===== CONFIG =====
BOT_TOKEN = "YOUR_BOT_TOKEN"
API_KEY = "YOUR_API_KEY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ===== BEST QUALITY =====
def get_best(file):
    streams = file.get("fast_stream_url", {})
    if streams:
        # highest quality (last value)
        return list(streams.values())[-1]
    return file.get("normal_dlink")


# ===== START =====
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("👋 Send Terabox link")


# ===== MAIN =====
@dp.message()
async def main(msg: types.Message):
    text = msg.text

    if not text or "terabox" not in text:
        return await msg.answer("❌ Send valid Terabox link")

    await msg.answer("⏳ Processing...")

    try:
        # fix link
        url = text
        if "teraboxshare.com" in text:
            url = text.replace("teraboxshare.com", "1024terabox.com")

        # ===== API CALL =====
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
            return await msg.answer("❌ No file found")

        # ===== BUTTON UI =====
        keyboard = []

        for file in files[:10]:
            best = get_best(file)

            keyboard.append([
                types.InlineKeyboardButton(
                    text=f"{file.get('name')} ({file.get('size_formatted')})",
                    callback_data=json.dumps({
                        "name": file.get("name"),
                        "size": file.get("size_formatted"),
                        "url": best
                    })
                )
            ])

        markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

        await msg.answer("📂 Select file 👇", reply_markup=markup)

    except Exception as e:
        await msg.answer(f"❌ Error:\n{str(e)}")


# ===== BUTTON CLICK =====
@dp.callback_query()
async def click(call: types.CallbackQuery):
    data = json.loads(call.data)

    text = (
        f"🎥 {data['name']}\n"
        f"📦 {data['size']}\n\n"
        f"⬇️ Best Quality:\n{data['url']}"
    )

    await call.message.answer(text)
    await call.answer()


# ===== RUN =====
async def main_run():
    print("🚀 Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main_run())
