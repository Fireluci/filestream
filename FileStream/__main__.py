import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers
from FileStream.config import Telegram, Server
from aiohttp import web
from pyrogram import idle

from FileStream.bot import FileStream
from FileStream.server import web_server
from FileStream.bot.clients import initialize_clients

logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        handlers.RotatingFileHandler(
            "streambot.log",
            mode="a",
            maxBytes=104857600,
            backupCount=2,
            encoding="utf-8"
        )
    ],
)

logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("aiohttp.web").setLevel(logging.ERROR)

server = web.AppRunner(web_server())
loop = asyncio.get_event_loop()


# -----------------------------------------------------------
# AUTO-RESTART SYSTEM:
# Starts daily at 5:00 PM IST, then repeats every 12 hours.
# -----------------------------------------------------------
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

async def auto_restart_cycle():
    while True:
        now = datetime.now(tz=IST)

        # Next 5 PM
        next_5pm = now.replace(hour=17, minute=0, second=0, microsecond=0)
        if next_5pm <= now:
            next_5pm += timedelta(days=1)

        # Time until next 5 PM
        wait_secs = (next_5pm - now).total_seconds()

        # Detect restart right after 5 PM → schedule 12 hours only
        # (because container restarts quickly)
        started_recently_after_5 = (now - (next_5pm - timedelta(days=1))).total_seconds() if now.hour >= 17 else -999

        if 0 <= started_recently_after_5 <= 300:
            # Within 5 mins after last restart at 5 PM → schedule 12h
            wait_secs = 12 * 3600
            print("[Auto-Restart] Detected fresh start after 5 PM. Next restart in 12 hours.")
        else:
            print(f"[Auto-Restart] Next restart scheduled at {next_5pm.isoformat()} IST ({wait_secs/3600:.2f} hours).")

        await asyncio.sleep(wait_secs)

        # Log restart
        timestamp = datetime.now(tz=IST).isoformat()
        msg = f"[Auto-Restart] {timestamp} — BOT RESTARTED (scheduled)"
        print("\n" + msg + "\n")
        logging.info(msg)

        # Try stopping FileStream safely
        try:
            await FileStream.stop()
        except Exception as e:
            print("[Auto-Restart] Error stopping FileStream:", e)

        # Cleanup web server
        try:
            await server.cleanup()
        except Exception as e:
            print("[Auto-Restart] Error cleaning web server:", e)

        # Exit → Koyeb auto restarts container
        print("[Auto-Restart] Exiting to let Koyeb restart container now.")
        sys.exit(0)


# -----------------------------------------------------------


async def start_services():
    print()
    if Telegram.SECONDARY:
        print("------------------ Starting as Secondary Server ------------------")
    else:
        print("------------------- Starting as Primary Server -------------------")
    print()
    print("-------------------- Initializing Telegram Bot --------------------")

    await FileStream.start()
    bot_info = await FileStream.get_me()
    FileStream.id = bot_info.id
    FileStream.username = bot_info.username
    FileStream.fname = bot_info.first_name

    print("------------------------------ DONE ------------------------------")
    print()
    print("---------------------- Initializing Clients ----------------------")
    await initialize_clients()
    print("------------------------------ DONE ------------------------------")
    print()
    print("--------------------- Initializing Web Server ---------------------")

    await server.setup()
    await web.TCPSite(server, Server.BIND_ADDRESS, Server.PORT).start()

    print("------------------------------ DONE ------------------------------")
    print()
    print("------------------------- Service Started -------------------------")
    print("                        bot =>>", bot_info.first_name)
    if bot_info.dc_id:
        print("                        DC ID =>>", str(bot_info.dc_id))
    print(" URL =>>", Server.URL)
    print("------------------------------------------------------------------")

    # Start the automatique restart scheduler
    loop.create_task(auto_restart_cycle())

    await idle()


async def cleanup():
    await server.cleanup()
    await FileStream.stop()


if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.error(traceback.format_exc())
    finally:
        loop.run_until_complete(cleanup())
        loop.stop()
        print("------------------------ Stopped Services ------------------------")
