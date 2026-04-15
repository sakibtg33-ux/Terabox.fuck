const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

// ===== ENV =====
const BOT_TOKEN = process.env.BOT_TOKEN;
const API_KEY = process.env.API_KEY;

// ===== BOT =====
const bot = new TelegramBot(BOT_TOKEN, { polling: true });

bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;

    // only terabox link
    if (!text || !text.includes("terabox")) {
        return bot.sendMessage(chatId, "❌ Send a valid Terabox link");
    }

    await bot.sendMessage(chatId, "⏳ Processing...");

    try {
        // ===== API CALL =====
        const res = await axios.post(
            "https://xapiverse.com/api/terabox",
            { url: text },
            {
                headers: {
                    "Content-Type": "application/json",
                    "xAPIverse-Key": API_KEY
                }
            }
        );

        // ===== VALIDATION =====
        if (!res.data || !res.data.list || res.data.list.length === 0) {
            return bot.sendMessage(chatId, "❌ No file found!");
        }

        const file = res.data.list[0];

        const downloadUrl = file.normal_dlink;

        if (!downloadUrl) {
            return bot.sendMessage(chatId, "❌ Download link not found!");
        }

        // ===== SIZE CHECK (50MB limit safe) =====
        if (file.size > 50 * 1024 * 1024) {
            return bot.sendMessage(chatId,
                `⚠️ File too large!\n\n📁 ${file.name}\n📦 ${file.size_formatted}\n\n⬇️ Download:\n${downloadUrl}`
            );
        }

        await bot.sendMessage(chatId,
            `📁 ${file.name}\n📦 ${file.size_formatted}\n\n📥 Downloading...`
        );

        // ===== DOWNLOAD =====
        const filePath = path.join(__dirname, `${Date.now()}.mp4`);
        const writer = fs.createWriteStream(filePath);

        const response = await axios({
            url: downloadUrl,
            method: "GET",
            responseType: "stream"
        });

        response.data.pipe(writer);

        writer.on("finish", async () => {
            try {
                await bot.sendVideo(chatId, filePath, {
                    caption: file.name
                });
            } catch (err) {
                await bot.sendMessage(chatId, "⚠️ Send failed, here is link:\n" + downloadUrl);
            }

            fs.unlinkSync(filePath);
        });

        writer.on("error", async () => {
            await bot.sendMessage(chatId, "❌ Download error!");
        });

    } catch (err) {
        console.log(err.response?.data || err.message);
        await bot.sendMessage(chatId, "❌ Processing failed!");
    }
});        const response = await axios({
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
