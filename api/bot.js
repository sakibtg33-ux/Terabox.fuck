import axios from "axios";

const TOKEN = process.env.BOT_TOKEN;
const API_KEY = process.env.API_KEY;

export default async function handler(req, res) {

    if (req.method !== "POST") {
        return res.status(200).send("OK");
    }

    const body = req.body;
    const msg = body.message;

    if (!msg) return res.status(200).send("no msg");

    const chatId = msg.chat.id;
    const text = msg.text;

    async function send(textMsg) {
        await axios.post(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
            chat_id: chatId,
            text: textMsg
        });
    }

    try {

        if (!text || !text.includes("terabox")) {
            await send("Send terabox link");
            return res.status(200).send("ok");
        }

        await send("Processing...");

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

        // 👇 FULL RESPONSE SEND
        await send("API RESPONSE:\n" + JSON.stringify(apiRes.data));

        return res.status(200).send("ok");

    } catch (err) {

        // 👇 REAL ERROR SHOW
        const errorMsg =
            err.response?.data?.message ||
            err.response?.data ||
            err.message;

        await send("ERROR:\n" + JSON.stringify(errorMsg));

        return res.status(200).send("error");
    }
}
