import os
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
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

    if query.data == "wait_image":
        await query.message.reply_text("📤 OK, send the image now.")
        return WAIT_IMAGE

    if query.data == "skip_image":
        return await show_preview(update, context)

    if query.data == "approve_post":
        user_id = update.effective_user.id
        text = user_data[user_id]["text"]
        image = user_data[user_id].get("image")
        
        try:
            status_code, resp = post_to_linkedin(text, image)
            # Consider both 200 (OK) and 202 (Accepted) as success status codes
            if status_code in (200, 201, 202):
                await query.message.reply_text("✅ Post submitted successfully! It may take a few moments to appear on LinkedIn.")
            else:
                await query.message.reply_text(f"❌ Failed to post. Status: {status_code}, Response: {resp}")
        except Exception as e:
            await query.message.reply_text(f"❌ An error occurred while posting: {str(e)}")
            
        user_data.pop(user_id, None)
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
    await update.message.reply_text("Do you want to add an image?", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAIT_IMAGE

async def receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        photo = update.message.photo[-1]  # Highest resolution
        file = await photo.get_file()
        file_path = f"/tmp/{user_id}.jpg"
        await file.download_to_drive(file_path)
        user_data[user_id]["image"] = file_path
        await update.message.reply_text("🖼️ Image received.")
        return await show_preview(update, context)
    except Exception as e:
        logger.error(f"❌ Error receiving image: {e}")
        await update.message.reply_text("⚠️ Failed to receive image. Try again.")
        return WAIT_IMAGE

async def show_preview(update_or_query, context):
    user_id = update_or_query.effective_user.id
    text = user_data[user_id]["text"]
    image = user_data[user_id].get("image")

    keyboard = [
        [InlineKeyboardButton("✏️ Edit", callback_data="edit_post"),
         InlineKeyboardButton("✅ Approve & Post", callback_data="approve_post")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if image and os.path.exists(image):
            with open(image, "rb") as img:
                await context.bot.send_photo(chat_id=user_id, photo=img)

        if hasattr(update_or_query, 'callback_query') and update_or_query.callback_query:
            await update_or_query.callback_query.message.reply_text(text, reply_markup=reply_markup)
        elif hasattr(update_or_query, 'message') and update_or_query.message:
            await update_or_query.message.reply_text(text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=user_id, text=text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"⚠️ Error in show_preview: {e}")
        await context.bot.send_message(chat_id=user_id, text="⚠️ Failed to show preview.")

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
                CallbackQueryHandler(button_handler, pattern="^wait_image$"),
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
