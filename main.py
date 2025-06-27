"""
Main entry point for the LinkedIn AI Poster application.

This module handles the initialization and coordination of the Telegram bot
and Flask web server components.
"""

import asyncio
import logging
import os
import signal
import sys
import threading
import traceback
from signal import Signals
from typing import Any, Optional, Dict, List, Set, Callable, Awaitable, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global variable to store the application instance
application: Any = None

# Global variable to store the Flask app
flask_app: Any = None

# Set to store all running tasks
running_tasks: Set[asyncio.Task] = set()

# Event to signal application shutdown
shutdown_event = asyncio.Event()

# Flag to track if we're in the process of shutting down
is_shutting_down = False

def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals.
    
    Args:
        signum: The signal number
        frame: The current stack frame
    """
    global is_shutting_down
    
    if is_shutting_down:
        logger.warning("Already shutting down, ignoring duplicate signal")
        return
        
    is_shutting_down = True
    logger.info(f"Received signal {signal.Signals(signum).name}, initiating graceful shutdown...")
    shutdown_event.set()

def start_bot() -> Any:
    """Initialize and return the Telegram bot application"""
    from bot import main as bot_main
    try:
        return bot_main()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}", exc_info=True)
        raise

def start_flask() -> Any:
    """Initialize and return the Flask application"""
    try:
        from web_login import app as flask_app
        return flask_app
    except Exception as e:
        logger.error(f"Failed to start Flask app: {e}", exc_info=True)
        raise

def create_task(coro: Awaitable, name: str = None) -> asyncio.Task:
    """Create a task and add it to the running tasks set"""
    task = asyncio.create_task(coro, name=name)
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)
    return task

async def shutdown_sequence() -> None:
    """Graceful shutdown sequence"""
    global application
    
    logger.info("Starting shutdown sequence...")
    
    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if tasks:
        logger.info(f"Cancelling {len(tasks)} running tasks...")
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Task completed with error during shutdown: {result}")
    
    # Stop the bot if it's running
    if application and hasattr(application, 'stop'):
        logger.info("Stopping bot...")
        try:
            await asyncio.wait_for(application.stop(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for bot to stop")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)
    
    logger.info("Shutdown complete")
    await asyncio.sleep(0.1)  # Give time for logs to flush

async def run_web_server() -> None:
    """Run the Flask web server in a separate thread."""
    try:
        from web_login import run_web_server as start_web_server
        logger.info("Starting web server...")
        start_web_server()
    except Exception as e:
        logger.error(f"Error in web server: {e}", exc_info=True)
        sys.exit(1)

async def run_bot() -> None:
    """Run the Telegram bot in the main thread."""
    global application
    try:
        logger.info("Starting Telegram bot...")
        application = start_bot()
        await application.initialize()
        await application.start()
        
        # Start polling for updates
        logger.info("Starting bot polling...")
        await application.updater.start_polling()
        
        # Keep the bot running until shutdown is requested
        while not shutdown_event.is_set():
            await asyncio.sleep(0.1)
            
    except asyncio.CancelledError:
        logger.info("Bot task was cancelled")
    except Exception as e:
        logger.error(f"Error in bot: {e}", exc_info=True)
        raise
    finally:
        if application:
            logger.info("Stopping bot...")
            try:
                await application.stop()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}", exc_info=True)
            
            try:
                if hasattr(application, 'updater') and application.updater.running:
                    logger.info("Stopping bot updater...")
                    await application.updater.stop()
            except Exception as e:
                logger.error(f"Error stopping updater: {e}", exc_info=True)

async def monitor_shutdown() -> None:
    """Monitor for shutdown events and handle them gracefully."""
    await shutdown_event.wait()
    logger.info("Shutdown event received, initiating shutdown sequence...")
    await shutdown_sequence()

async def main() -> None:
    """Main entry point for the application."""
    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler, sig, None)
    
    # Start web server in a separate thread
    logger.info("Starting web server thread...")
    web_thread = threading.Thread(target=lambda: asyncio.run(run_web_server()), daemon=True)
    web_thread.start()
    
    # Start the bot in the main thread
    bot_task = create_task(run_bot(), name="bot_task")
    
    # Start the shutdown monitor
    monitor_task = create_task(monitor_shutdown(), name="shutdown_monitor")
    
    try:
        # Wait for the bot task to complete (it shouldn't unless there's an error)
        await asyncio.wait_for(bot_task, timeout=None)
    except asyncio.CancelledError:
        logger.info("Main task was cancelled")
    except Exception as e:
        logger.error(f"Error in main task: {e}", exc_info=True)
    finally:
        # Ensure we trigger a shutdown if we get here
        if not shutdown_event.is_set():
            shutdown_event.set()
        
        # Wait for the shutdown sequence to complete
        await asyncio.wait_for(monitor_task, timeout=10.0)
        
        # Cancel any remaining tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            logger.info(f"Cancelling {len(tasks)} remaining tasks...")
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

def run() -> None:
    """Run the application with proper error handling."""
    try:
        # Run the main application
        logger.info("Starting application...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")

if __name__ == '__main__':
    run()
