import TelegramBot from "node-telegram-bot-api";
import dotenv from "dotenv";

dotenv.config();

const bot = new TelegramBot(process.env.BOT_TOKEN, {
  polling: true
});

console.log("🤖 Bot started...");

// Message handler
bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text;

  if (!text) return;

  // Only terabox link
  if (!text.includes("terabox")) {
    return bot.sendMessage(chatId, "❌ Send a valid TeraBox link");
  }

  bot.sendMessage(chatId, "⏳ Processing...");

  try {
    const res = await fetch("https://xapiverse.com/api/terabox", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "xAPIverse-Key": process.env.API_KEY
      },
      body: JSON.stringify({ url: text })
    });

    const data = await res.json();

    console.log("API RESPONSE:", data);

    // Check success
    if (!res.ok) {
      return bot.sendMessage(chatId, "❌ API Error:\n" + JSON.stringify(data));
    }

    // Extract link safely
    const link =
      data?.data?.download_url ||
      data?.data?.url ||
      data?.download_url;

    if (!link) {
      return bot.sendMessage(chatId, "❌ No download link found");
    }

    bot.sendMessage(chatId, `✅ Download Link:\n${link}`);
  } catch (err) {
    console.error(err);
    bot.sendMessage(chatId, "❌ Server Error");
  }
});    bot.sendMessage(chatId, "❌ Error occurred");
  }
});
