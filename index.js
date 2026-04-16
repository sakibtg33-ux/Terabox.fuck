import TelegramBot from "node-telegram-bot-api";
import fetch from "node-fetch";
import dotenv from "dotenv";

dotenv.config();

const bot = new TelegramBot(process.env.BOT_TOKEN, { polling: true });

bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  if (!text.includes("terabox")) {
    return bot.sendMessage(chatId, "❌ Send valid TeraBox link");
  }

  bot.sendMessage(chatId, "⏳ Processing...");

  try {
    const res = await fetch("https://xapiverse.com/api/terabox-pro", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "xAPIverse-Key": process.env.API_KEY
      },
      body: JSON.stringify({ url: text })
    });

    const data = await res.json();

    if (!data?.data?.download_url) {
      return bot.sendMessage(chatId, "❌ Failed to get link");
    }

    bot.sendMessage(chatId, `✅ Download:\n${data.data.download_url}`);
  } catch (err) {
    bot.sendMessage(chatId, "❌ Error occurred");
  }
});
