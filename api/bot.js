import axios from "axios";

const TOKEN = process.env.BOT_TOKEN;
const API_KEY = process.env.API_KEY;

export default async function handler(req, res) {

    if (req.method !== "POST") {
        return res.status(200).send("Bot is running...");
    }

    const body = req.body;
    const msg = body.message;

    const chatId = msg?.chat?.id;
    const text = msg?.text;

    async function sendMessage(textMsg) {
        await axios.post(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
            chat_id: chatId,
            text: textMsg
        });
    }

    try {
        if (!text || !text.includes("terabox")) {
            await sendMessage("❌ Send valid Terabox link");
            return res.status(200).send("ok");
        }

        await sendMessage("⏳ Processing...");

        const apiRes = await axios.post(
            "https://xapiverse.com/api/terabox",
            { url: text },
            {
                headers: {
                    "Content-Type": "application/json",
                    "xAPIverse-Key": API_KEY
                }
            }
        );

        if (!apiRes.data || !apiRes.data.list || apiRes.data.list.length === 0) {
            await sendMessage("❌ No file found");
            return res.status(200).send("ok");
        }

        const file = apiRes.data.list[0];

        const download = file.normal_dlink;
        const fast480 = file.fast_stream_url?.["480p"];

        let reply = `📁 ${file.name}\n📦 ${file.size_formatted}\n\n`;

        if (download) {
            reply += `⬇️ Download:\n${download}\n\n`;
        }

        if (fast480) {
            reply += `⚡ Stream (480p):\n${fast480}`;
        }

        await sendMessage(reply);

        return res.status(200).send("ok");

    } catch (err) {
        await sendMessage("❌ Error: " + (err.response?.data?.message || err.message));
        return res.status(200).send("error");
    }
}
