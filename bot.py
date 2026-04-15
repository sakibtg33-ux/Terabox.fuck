import asyncio
import json
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = "YOUR_BOT_TOKEN"
API_KEY = "YOUR_API_KEY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def get_best(file):
    streams = file.get("fast_stream_url", {})
    if streams:
        return list(streams.values())[-1]
    return file.get("normal_dlink")


@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("👋 Send Terabox link")


@dp.message()
async def main(msg: types.Message):
    text = msg.text

    if not text or "terabox" not in text:
        return await msg.answer("❌ Send valid link")

    await msg.answer("⏳ Processing...")

    try:
        url = text
        if "teraboxshare.com" in text:
            url = text.replace("teraboxshare.com", "1024terabox.com")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://xapiverse.com/api/terabox",
                json={"url": url},
                headers={
                    "Content-Type": "application/json",
                    "xAPIverse-Key": API_KEY
                },
                timeout=15
            ) as res:
                data = await res.json()

        files = data.get("list", [])

        if not files:
            return await msg.answer("❌ No file found")

        keyboard = []

        for file in files[:10]:
            best = get_best(file)

            keyboard.append([
                types.InlineKeyboardButton(
                    text=file.get("name"),
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


@dp.callback_query()
async def click(call: types.CallbackQuery):
    data = json.loads(call.data)

    text = f"🎥 {data['name']}\n📦 {data['size']}\n\n⬇️ {data['url']}"

    await call.message.answer(text)
    await call.answer()


# ===== AUTO RESTART LOOP =====
async def main_run():
    while True:
        try:
            print("🚀 Bot running...")
            await dp.start_polling(bot)
        except Exception as e:
            print("❌ Crash:", e)
            await asyncio.sleep(5)  # wait and restart


if __name__ == "__main__":
    asyncio.run(main_run())
