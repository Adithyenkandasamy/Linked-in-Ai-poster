import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from telegram.ext import filters

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# Temporary user state (no DB)
user_states = {}

# Start menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Received /start command from user {update.effective_user.id}")
        keyboard = [
            [InlineKeyboardButton("🔐 Login", callback_data='login')],
            [InlineKeyboardButton("📝 Post", callback_data='post')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("👋 Welcome! What would you like to do?", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        if update.message:
            await update.message.reply_text("❌ An error occurred. Please try again later.")

# Button clicks
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.callback_query:
            logger.error("No callback_query in update")
            return
            
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        logger.info(f"Button pressed by user {user_id}: {query.data}")

        if query.data == 'login':
            try:
                login_url = f"http://localhost:5000/login?user={user_id}"
                await query.edit_message_text(f"🔐 Click to login: {login_url}")
            except Exception as e:
                logger.error(f"Error in login handler: {e}")
                await query.edit_message_text("❌ Failed to process login. Please try again.")

        elif query.data == 'post':
            try:
                user_states[user_id] = {'step': 'waiting_topic'}
                await query.edit_message_text("📌 What's the topic of your LinkedIn post?")
            except Exception as e:
                logger.error(f"Error in post handler: {e}")
                await query.edit_message_text("❌ Failed to start post creation. Please try again.")

        elif query.data == 'logout':
            try:
                user_states.pop(user_id, None)
                keyboard = [
                    [InlineKeyboardButton("📝 Post Again", callback_data='post')],
                    [InlineKeyboardButton("🔐 Login", callback_data='login')]
                ]
                await query.edit_message_text("🚪 You have logged out. Want to post again?", reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception as e:
                logger.error(f"Error in logout handler: {e}")
                await query.edit_message_text("❌ Failed to log out. Please try again.")
        else:
            logger.warning(f"Unknown button pressed: {query.data}")
            await query.edit_message_text("❌ Unknown command. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in handle_buttons: {e}")
        if 'query' in locals():
            await query.edit_message_text("❌ An unexpected error occurred. Please try again.")

# Handle text and image
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.from_user:
            logger.error("No message or from_user in update")
            return
            
        user_id = update.message.from_user.id
        logger.info(f"Message received from user {user_id}")
        state = user_states.get(user_id)

        if not state:
            await update.message.reply_text("❗ Please start with /start")
            return

        step = state.get("step")

        if step == "waiting_topic":
            try:
                user_states[user_id]['topic'] = update.message.text
                user_states[user_id]['step'] = 'waiting_image'
                await update.message.reply_text("🖼️ Send an image (optional), or type 'skip'.")
            except Exception as e:
                logger.error(f"Error in waiting_topic handler: {e}")
                await update.message.reply_text("❌ Failed to process your topic. Please try again.")

        elif step == "waiting_image":
            try:
                if update.message.text and update.message.text.lower() == 'skip':
                    user_states[user_id]['image'] = None
                    user_states[user_id]['step'] = 'generating'
                    await update.message.reply_text("🧠 Generating content using AI...")
                    # placeholder for AI and posting step
                elif update.message.photo:
                    user_states[user_id]['image'] = update.message.photo[-1].file_id
                    user_states[user_id]['step'] = 'generating'
                    await update.message.reply_text("🧠 Got image. Generating content using AI...")
                    # placeholder for AI and posting step
            except Exception as e:
                logger.error(f"Error in waiting_image handler: {e}")
                await update.message.reply_text("❌ Failed to process your image. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in handle_message: {e}")
        if 'update' in locals() and update.message:
            await update.message.reply_text("❌ An unexpected error occurred. Please try again.")

async def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    # Start the Bot
    print("Bot is running...")
    await application.initialize()
    await application.start()
    await application.run_polling()

    # This will never be reached but is good practice to have
    await application.stop()
    await application.shutdown()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
