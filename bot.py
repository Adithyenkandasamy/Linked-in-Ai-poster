import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

class LinkedInPosterBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_message = (
            "🤖 Welcome to LinkedIn AI Poster Bot!\n\n"
            "I can help you create and post content on LinkedIn.\n"
            "Just send me a topic or idea, and I'll generate a professional post for you!"
        )
        await update.message.reply_text(welcome_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_message = update.message.text
        # Here we'll integrate with our AI content generator
        response = f"I'll create a LinkedIn post about: {user_message}"
        await update.message.reply_text(response)

    def run(self):
        print("Starting bot...")
        self.app.run_polling()

if __name__ == "__main__":
    bot = LinkedInPosterBot()
    bot.run()
