# bot.py
import os
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from linkedin_api import post_to_linkedin
from gemini_ai import generate_post
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger("Bot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID"))

(
    WAIT_TOPIC,
    WAIT_IMAGE,
    WAIT_EDIT_DECISION,
    WAIT_FINAL_APPROVAL,
) = range(4)

# temporary in-memory store
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != AUTHORIZED_USER_ID:
        await update.message.reply_text("⛔ Access denied.")
        return
    keyboard = [[InlineKeyboardButton("📝 Post", callback_data="start_post")]]
    await update.message.reply_text("👋 Welcome! Choose an option:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != AUTHORIZED_USER_ID:
        await query.message.reply_text("⛔ Access denied.")
        return

    if query.data == "start_post":
        await query.message.reply_text("🧠 What topic should the LinkedIn post be about?")
        return WAIT_TOPIC

    if query.data == "skip_image":
        return await show_preview(update, context)

    if query.data == "approve_post":
        text = user_data[update.effective_user.id]["text"]
        image = user_data[update.effective_user.id].get("image")
        status_code, resp = post_to_linkedin(text, image)
        if status_code == 201:
            await query.message.reply_text("✅ Post published successfully!")
        else:
            await query.message.reply_text(f"❌ Failed to post. Error: {resp}")
        return ConversationHandler.END

    if query.data == "edit_post":
        await query.message.reply_text("✏️ Send the new edited content:")
        return WAIT_FINAL_APPROVAL

async def receive_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = update.message.text
    await update.message.reply_text("💡 Generating content using AI...")
    ai_text = generate_post(topic)
    user_data[update.effective_user.id] = {"text": ai_text}

    keyboard = [
        [InlineKeyboardButton("📎 Upload Image", callback_data="wait_image"),
         InlineKeyboardButton("⏭️ Skip", callback_data="skip_image")]
    ]
    await update.message.reply_text(
        "Do you want to add an image?", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAIT_IMAGE

async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.effective_attachment.get_file()
    file_path = f"/tmp/{update.effective_user.id}.jpg"
    await file.download_to_drive(file_path)
    user_data[update.effective_user.id]["image"] = file_path
    return await show_preview(update, context)

async def show_preview(update_or_query, context):
    user_id = update_or_query.effective_user.id
    text = user_data[user_id]["text"]
    image = user_data[user_id].get("image")

    keyboard = [
        [InlineKeyboardButton("✏️ Edit", callback_data="edit_post"),
         InlineKeyboardButton("✅ Approve & Post", callback_data="approve_post")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Handle both CallbackQuery and Message objects
    if hasattr(update_or_query, 'callback_query'):
        # It's a CallbackQuery
        message = update_or_query.callback_query.message
        await message.reply_text(text, reply_markup=reply_markup)
    elif hasattr(update_or_query, 'message'):
        # It's a Message
        await update_or_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        # Fallback
        await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

    return WAIT_EDIT_DECISION

async def receive_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id]["text"] = update.message.text
    return await show_preview(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    user_data.pop(update.effective_user.id, None)
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^start_post$")],
        states={
            WAIT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic)],
            WAIT_IMAGE: [
                CallbackQueryHandler(button_handler, pattern="^skip_image$"),
                MessageHandler(filters.PHOTO, receive_image)
            ],
            WAIT_EDIT_DECISION: [CallbackQueryHandler(button_handler)],
            WAIT_FINAL_APPROVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edited)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Bot running.")
    app.run_polling()

if __name__ == "__main__":
    main()
