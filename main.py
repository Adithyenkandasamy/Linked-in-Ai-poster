import asyncio
import threading
import logging
from web_login import app as flask_app
from bot import main as start_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_flask():
    """Run the Flask web server"""
    try:
        logger.info("Starting Flask server on http://localhost:5000")
        flask_app.run(port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask server error: {e}")
        raise

async def main():
    """Main async function to start both Flask and Telegram bot"""
    try:
        # Start Flask in a separate thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Start the Telegram bot
        logger.info("Starting Telegram bot...")
        application = start_bot()
        
        # Run the application
        await application.initialize()
        await application.start()
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise
    finally:
        # Cleanup code if needed
        logger.info("Shutting down application...")
        try:
            await application.stop()
            await application.shutdown()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
