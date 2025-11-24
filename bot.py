import os
import re
import pandas as pd
import pytesseract
from pdf2image import convert_from_path
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes

from keep_alive import keep_alive

TOKEN = os.getenv("BOT_TOKEN")

PATTERN = re.compile(r"(\d{1,4})\s+([A-Z0-9]{10,})")

# Poppler path for Replit
POPPLER_PATH = "/home/runner/.apt/usr/bin"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a Bengali voter list PDF.\nI will extract Serial No + Voter ID.")


async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    pdf_path = "input.pdf"
    await file.download_to_drive(pdf_path)

    try:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
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
        await update.message.reply_text("No data found in PDF.")
        return

    df = pd.DataFrame(rows)
    output_path = "voter.xlsx"
    df.to_excel(output_path, index=False)

    await update.message.reply_document(document=open(output_path, "rb"))


async def main():
    keep_alive()  # prevents replit sleeping

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FILE_EXTENSION("pdf"), handle_pdf))

    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
