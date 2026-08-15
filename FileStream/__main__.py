import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers
from datetime import datetime, timedelta, timezone
from aiohttp import web
from pyrogram import idle

from FileStream.config import Telegram, Server
from FileStream.bot import FileStream
from FileStream.server import web_server
from FileStream.bot.clients import initialize_clients

# OWNER ID from config
OWNER_ID = Telegram.OWNER_ID

# ---------------------------------------------------------
# TIME FORMATTER → "2 Dec 2025 | 6:32 PM"
# ---------------------------------------------------------
def fmt_time(dt):
    return dt.strftime("%-d %b %Y | %-I:%M %p")

# Logging
logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        logging.handlers.RotatingFileHandler(
            "streambot.log",
            mode="a",
            maxBytes=104857600,
            backupCount=2,
            encoding="utf-8"
        )
    ],
)

# FIXED: Allowed aiohttp logs to pass through so web requests/pings can be seen
logging.getLogger("aiohttp").setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# FIXED: Added request logging middleware to track UptimeRobot / external pings in console
@web.middleware
async def request_logger_middleware(request, handler):
    logging.info(f"[Ping] Incoming request: {request.method} {request.path} from {request.remote}")
    return await handler(request)

# Pass the logging middleware into the web server application instance
_app = web_server()
if _app._middlewares is None:
    _app._middlewares = []
_app._middlewares.append(request_logger_middleware)

server = web.AppRunner(_app)
loop = asyncio.get_event_loop()
IST = timezone(timedelta(hours=5, minutes=30))


# --------------------------------------------------------------------
# STARTUP
# --------------------------------------------------------------------
async def start_services():
    print("\n------------------- Starting as Primary Server -------------------\n")

    print("-------------------- Initializing Telegram Bot --------------------")
    await FileStream.start()
    bot_info = await FileStream.get_me()
    FileStream.id = bot_info.id
    FileStream.username = bot_info.username
    FileStream.fname = bot_info.first_name
    print("------------------------------ DONE ------------------------------\n")

    # Startup notify
    try:
        timestamp = fmt_time(datetime.now(tz=IST))
        start_msg = (
            f"🚀 BOT STARTED\n"
            f"⏰ {timestamp}\n"
            f"📌 Reason: Deploy / Restart"
        )
        await FileStream.send_message(OWNER_ID, start_msg)
        print("[Startup] Notified owner.")
    except:
        print("[Startup] Failed to notify owner.")

    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------\n")

    print("--------------------- Initializing Web Server ---------------------")
    await server.setup()
    await web.TCPSite(server, Server.BIND_ADDRESS, Server.PORT).start()
    print("------------------------------ DONE ------------------------------\n")

    print("------------------------- Service Started -------------------------")
    print("                        bot =>>", bot_info.first_name)
    if bot_info.dc_id:
        print("                        DC ID =>>", bot_info.dc_id)
    print(" URL =>>", Server.URL)
    print("------------------------------------------------------------------")

    await idle()


# --------------------------------------------------------------------
# CLEANUP
# --------------------------------------------------------------------
async def cleanup():
    try: await server.cleanup()
    except: pass

    try: await FileStream.stop()
    except: pass


# --------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------
if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        print("[Main] Process interrupted by user.")
    except Exception:
        logging.error(traceback.format_exc())
    finally:
        try:
            loop.run_until_complete(cleanup())
        except:
            pass

        loop.stop()
        print("------------------------ Stopped Services ------------------------")
