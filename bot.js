const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const BOT_TOKEN = process.env.BOT_TOKEN;
const API_KEY = process.env.API_KEY;

const bot = new TelegramBot(BOT_TOKEN, { polling: true });

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;

    if (!text || !text.includes("terabox")) {
        return bot.sendMessage(chatId, "❌ Send Terabox link");
    }

    bot.sendMessage(chatId, "⏳ Processing...");

    try {
        const res = await axios.post(
            "https://xapiverse.com/api/terabox-pro",
            { url: text },
            {
                headers: { "xAPIverse-Key": API_KEY }
            }
        );

        const file = res.data.list[0];

        bot.sendMessage(chatId, `📥 Downloading:\n${file.name}`);

        const filePath = path.join(__dirname, `${Date.now()}.mp4`);
        const writer = fs.createWriteStream(filePath);

        const response = await axios({
            url: file.download_link,
            method: "GET",
            responseType: "stream"
        });

        response.data.pipe(writer);

        writer.on("finish", async () => {
            await bot.sendVideo(chatId, filePath, {
                caption: file.name
            });

            fs.unlinkSync(filePath);
        });

    } catch (err) {
        console.log(err);
        bot.sendMessage(chatId, "❌ Failed");
    }
});
