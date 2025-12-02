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

# -----------------------------------------------------------
# LOGGING
# -----------------------------------------------------------
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
# AUTO RESTART (6 AM + 6 PM)
# -----------------------------------------------------------
from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))

async def auto_restart_cycle():
    while True:
        now = datetime.now(tz=IST)

        # Default next restart is today 6 PM
        next_6 = now.replace(hour=18, minute=0, second=0, microsecond=0)

        if now.hour < 6 or (now.hour == 6 and now.minute == 0):
            # Before 6 AM → restart today at 6 AM
            next_6 = now.replace(hour=6, minute=0, second=0, microsecond=0)
        elif 6 <= now.hour < 18:
            # Between 6 AM & 6 PM → restart at 6 PM
            next_6 = now.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # After 6 PM → restart next day 6 AM
            next_6 = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)

        wait_secs = (next_6 - now).total_seconds()
        print(f"[Auto-Restart] Next restart at {next_6.isoformat()} IST ({wait_secs/3600:.2f} hours).")

        await asyncio.sleep(wait_secs)

        # Restart message
        timestamp = datetime.now(tz=IST).isoformat()
        msg = f"♻️ BOT RESTARTED\n⏰ {timestamp}\n🔁 Auto-Restart at 6 AM / 6 PM"

        print("\n" + msg + "\n")
        logging.info(msg)

        # Send to log channel
        try:
            await FileStream.send_message(
                chat_id=Telegram.FLOG_CHANNEL,
                text=msg
            )
        except Exception as e:
            print("[Auto-Restart] Failed sending to FLOG_CHANNEL:", e)

        # --- Graceful Shutdown ---
        try: await FileStream.stop()
        except: pass

        try:
            await FileStream._client.disconnect()
        except: pass

        try:
            await FileStream.session.stop()
        except: pass

        try: await server.cleanup()
        except: pass

        print("[Auto-Restart] Exiting — Koyeb will restart container.")
        sys.exit(0)


# -----------------------------------------------------------
# START SERVICES
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

    # ⭐ START AUTO-RESTART LOOP (correct placement)
    loop.create_task(auto_restart_cycle())

    # Keep the bot alive
    await idle()


# -----------------------------------------------------------
# CLEANUP
# -----------------------------------------------------------
async def cleanup():
    await server.cleanup()
    await FileStream.stop()


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
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
