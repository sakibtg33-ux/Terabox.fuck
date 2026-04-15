import asyncio
import json
import aiohttp
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

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
        return await msg.answer("❌ Send valid Terabox link")

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
                }
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


@dp.callback_query()
async def click(call: types.CallbackQuery):
    data = json.loads(call.data)

    text = (
        f"🎥 {data['name']}\n"
        f"📦 {data['size']}\n\n"
        f"⬇️ {data['url']}"
    )

    await call.message.answer(text)
    await call.answer()


async def main_run():
    while True:
        try:
            print("🚀 Bot running...")
            await dp.start_polling(bot)
        except Exception as e:
            print("❌ Crash:", e)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main_run())
