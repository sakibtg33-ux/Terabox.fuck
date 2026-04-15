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
            await send("❌ Send a valid Terabox link");
            return res.status(200).send("ok");
        }

        await send("⏳ Processing...");

        // ===== FIX LINK (teraboxshare → 1024terabox)
        let fixedUrl = text;
        if (text.includes("teraboxshare.com")) {
            fixedUrl = text.replace("teraboxshare.com", "1024terabox.com");
        }

        // ===== API CALL
        const apiRes = await axios.post(
            "https://xapiverse.com/api/terabox",
            { url: fixedUrl },
            {
                headers: {
                    "Content-Type": "application/json",
                    "xAPIverse-Key": API_KEY
                }
            }
        );

        // ===== CHECK RESPONSE
        if (!apiRes.data?.list?.length) {
            await send("❌ No downloadable file found!");
            return res.status(200).send("ok");
        }

        const file = apiRes.data.list[0];

        // ===== NON-VIDEO FILE HANDLE
        if (file.type !== "video") {
            await send(
                `⚠️ File: ${file.name}\n📦 ${file.size_formatted}\n\n⬇️ Download:\n${file.normal_dlink}`
            );
            return res.status(200).send("ok");
        }

        // ===== VIDEO RESPONSE
        let msg = `🎥 ${file.name}\n📦 ${file.size_formatted}\n\n`;

        if (file.normal_dlink) {
            msg += `⬇️ Download:\n${file.normal_dlink}\n\n`;
        }

        if (file.fast_stream_url?.["480p"]) {
            msg += `⚡ Stream:\n${file.fast_stream_url["480p"]}`;
        }

        await send(msg);

        return res.status(200).send("ok");

    } catch (err) {

        const errorMsg =
            err.response?.data?.message ||
            JSON.stringify(err.response?.data) ||
            err.message;

        await send("❌ Failed:\n" + errorMsg);

        return res.status(200).send("error");
    }
}
