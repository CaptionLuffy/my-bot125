import os
import re
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # e.g. https://your-render-app.onrender.com/webhook

bot = Bot(token=TOKEN)

app = Flask(__name__)

PATTERN = re.compile(r"(\d{1,4})\s+([A-Z0-9]{10,})")


# ---------------------- TELEGRAM HANDLERS ----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Webhook bot active!\nSend me the Bengali voter PDF.")


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):

    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    try:
        images = convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        await update.message.reply_text(f"PDF error: {e}")
        return

    rows = []

    for page_no, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang="ben")
        for line in text.splitlines():
            m = PATTERN.search(line)
            if m:
                rows.append({
                    "serial_no": m.group(1),
                    "voter_id": m.group(2),
                    "page": page_no + 1
                })

    if not rows:
        await update.message.reply_text("No Serial/Voter ID found.")
        return

    df = pd.DataFrame(rows)
    out_path = "voter.xlsx"
    df.to_excel(out_path, index=False)

    await update.message.reply_document(document=open(out_path, "rb"))


# ---------------------- FLASK WEBHOOK SERVER ----------------------

@app.route("/", methods=["GET"])
def index():
    return "Webhook OCR Bot Active!"

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    application.process_update(update)
    return "OK", 200


# ---------------------- START WEBHOOK ----------------------

if __name__ == "__main__":

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    # Delete old webhook
    bot.delete_webhook()

    # Set new webhook
    bot.set_webhook(url=WEBHOOK_URL)

    print("Webhook set:", WEBHOOK_URL)

    # Start Flask (Render Web Service)
    app.run(host="0.0.0.0", port=10000)
