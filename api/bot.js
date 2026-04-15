import axios from "axios";

const TOKEN = process.env.BOT_TOKEN;
const API_KEY = process.env.API_KEY;

export default async function handler(req, res) {

    if (req.method !== "POST") {
        return res.status(200).send("Bot running...");
    }

    const body = req.body;

    const message = body.message || body.edited_message;

    if (!message) {
        return res.status(200).send("No message");
    }

    const chatId = message.chat.id;
    const text = message.text;

    async function send(textMsg) {
        await axios.post(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
            chat_id: chatId,
            text: textMsg
        });
    }

    try {

        if (!text || !text.includes("terabox")) {
            await send("❌ Send Terabox link");
            return res.status(200).send("ok");
        }

        await send("⏳ Processing...");

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

        if (!apiRes.data?.list?.length) {
            await send("❌ No file found");
            return res.status(200).send("ok");
        }

        const file = apiRes.data.list[0];

        let msgText = `📁 ${file.name}\n📦 ${file.size_formatted}\n\n`;

        if (file.normal_dlink) {
            msgText += `⬇️ Download:\n${file.normal_dlink}\n\n`;
        }

        if (file.fast_stream_url?.["480p"]) {
            msgText += `⚡ Stream:\n${file.fast_stream_url["480p"]}`;
        }

        await send(msgText);

        return res.status(200).send("ok");

    } catch (err) {
        console.log(err.response?.data || err.message);
        await send("❌ Failed: " + (err.message));
        return res.status(200).send("error");
    }
}
