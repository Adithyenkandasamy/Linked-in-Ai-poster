# bot.py
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from linkedin_api import post_to_linkedin
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger("Bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID"))

POST_CONTENT = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    await update.message.reply_text("👋 Welcome! Use /post to share something on LinkedIn.")

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    await update.message.reply_text("✏️ Please send the text you'd like to post.")
    return POST_CONTENT

async def receive_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    status_code, resp = post_to_linkedin(text)
    if status_code == 201:
        await update.message.reply_text("✅ Post published successfully!")
    else:
        await update.message.reply_text(f"❌ Failed to post. Error: {resp}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("post", post_command)],
        states={POST_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_content)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()
