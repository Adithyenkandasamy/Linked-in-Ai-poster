import asyncio
import threading
from web_login import app as flask_app
from bot import main as start_bot

def run_flask():
    flask_app.run(port=5000)

async def main():
    threading.Thread(target=run_flask, daemon=True).start()
    await start_bot()

if __name__ == "__main__":
    asyncio.run(main())
