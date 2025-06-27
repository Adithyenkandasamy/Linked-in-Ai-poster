import os
import logging
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes
from telegram.ext import filters
from ai_content import generate_linkedin_post
from web_login import user_sessions
import asyncio

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

# User state management
user_states = {}

# Store temporary files
temp_dir = Path(tempfile.gettempdir()) / "linkedin_bot"
temp_dir.mkdir(exist_ok=True)

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
            return
            
        user_id = update.message.from_user.id
        state = user_states.get(user_id, {})
        
        if 'step' not in state:
            await update.message.reply_text("❗ Please start with /start")
            return
            
        step = state.get("step")
        
        if step == "waiting_topic":
            try:
                topic = update.message.text
                if not topic or len(topic) < 5:
                    await update.message.reply_text("❌ Please provide a valid topic (at least 5 characters).")
                    return
                    
                user_states[user_id]['topic'] = topic
                user_states[user_id]['step'] = 'waiting_image'
                await update.message.reply_text("🖼️ Send an image (optional), or type 'skip' to continue without an image.")
            except Exception as e:
                logger.error(f"Error in waiting_topic handler: {e}")
                await update.message.reply_text("❌ Failed to process your topic. Please try again.")
                
        elif step == "waiting_image":
            try:
                if update.message.text and update.message.text.lower() == 'skip':
                    user_states[user_id]['image'] = None
                    await generate_and_post(update, user_id)
                elif update.message.photo:
                    # Get the highest quality photo
                    photo = update.message.photo[-1]
                    file = await context.bot.get_file(photo.file_id)
                    
                    # Save the image temporarily
                    image_path = temp_dir / f"{user_id}_post_image.jpg"
                    await file.download_to_drive(image_path)
                    user_states[user_id]['image_path'] = str(image_path)
                    await generate_and_post(update, user_id)
                else:
                    await update.message.reply_text("❌ Please send an image or type 'skip' to continue without one.")
            except Exception as e:
                logger.error(f"Error in waiting_image handler: {e}")
                await update.message.reply_text("❌ Failed to process your image. Please try again.")
                
    except Exception as e:
        logger.error(f"Unexpected error in handle_message: {e}")
        if 'update' in locals() and update.message:
            await update.message.reply_text("❌ An unexpected error occurred. Please try again.")

async def generate_and_post(update: Update, user_id: int):
    try:
        state = user_states.get(user_id, {})
        topic = state.get('topic')
        
        # Generate content using AI
        await update.message.reply_text("🧠 Generating content using AI...")
        post_content = generate_linkedin_post(topic)
        
        if not post_content or post_content.startswith("⚠️"):
            await update.message.reply_text("❌ Failed to generate content. Please try again.")
            return
            
        # Check if user is logged in
        if user_id not in user_sessions:
            await update.message.reply_text("🔒 Please log in to LinkedIn first using the 'Login' button.")
            return
            
        # Post to LinkedIn
        await update.message.reply_text("🚀 Posting to LinkedIn...")
        linkedin_context = user_sessions[user_id]
        image_path = state.get('image_path')
        
        try:
            from linkedin_helper import post_to_linkedin
            post_url = post_to_linkedin(linkedin_context, post_content, image_path)
            
            # Clean up
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
                
            if post_url:
                await update.message.reply_text(f"✅ Successfully posted to LinkedIn!\n\n{post_url}")
            else:
                await update.message.reply_text("✅ Post might have been successful, but couldn't get the post URL.")
                
        except Exception as e:
            logger.error(f"Error posting to LinkedIn: {e}")
            await update.message.reply_text(f"❌ Failed to post to LinkedIn: {str(e)}")
            
        # Reset user state
        if user_id in user_states:
            del user_states[user_id]
            
    except Exception as e:
        logger.error(f"Error in generate_and_post: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
        if user_id in user_states:
            del user_states[user_id]

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_buttons))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    logger.info("Bot is running...")
    return application

if __name__ == '__main__':
    import asyncio
    application = main()
    asyncio.run(application.run_polling())
