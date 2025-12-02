import sys
import asyncio
import logging
import traceback
import logging.handlers as handlers
from FileStream.config import Telegram, Server, OWNER_ID
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
# TEST AUTO RESTART — EVERY 3 MINUTES
# -----------------------------------------------------------
from datetime import datetime, timedelta, timezone
IST = timezone(timedelta(hours=5, minutes=30))

async def auto_restart_cycle():
    # TEST MODE: restart every 3 minutes
    wait_secs = 3 * 60
    next_time = datetime.now(tz=IST) + timedelta(seconds=wait_secs)

    print(f"[TEST-RESTART] Restart scheduled at {next_time.isoformat()} IST (in 3 minutes).")
    await asyncio.sleep(wait_secs)

    timestamp = datetime.now(tz=IST).isoformat()
    msg = (
        f"♻️ BOT RESTARTED (TEST)\n"
        f"⏰ {timestamp}\n"
        f"🧪 Auto-restart triggered after 3 minutes (TEST MODE)"
    )

    print("\n" + msg + "\n")
    logging.info(msg)

    # ⭐ SEND TO OWNER ONLY
    try:
        await FileStream.send_message(chat_id=OWNER_ID, text=msg)
        print(f"[TEST-RESTART] Sent restart notice to OWNER: {OWNER_ID}")
    except Exception as e:
        print(f"[TEST-RESTART] Failed sending restart notice to OWNER: {e}")

    # Graceful shutdown
    try: await FileStream.stop()
    except: pass

    try: await FileStream._client.disconnect()
    except: pass

    try:
        await FileStream.session.stop()
    except: pass

    try: await server.cleanup()
    except: pass

    print("[TEST-RESTART] Exiting — Koyeb will restart container.")
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

    # ⭐ SEND STARTUP NOTICE TO OWNER
    try:
        start_msg = (
            f"🚀 BOT STARTED\n"
            f"⏰ {datetime.now(tz=IST).isoformat()}\n"
            f"📌 Reason: Fresh Boot / Deploy / Manual Start"
        )
        await FileStream.send_message(chat_id=OWNER_ID, text=start_msg)
        print(f"[Startup] Sent startup message to OWNER: {OWNER_ID}")
    except Exception as e:
        print("[Startup] Failed to send startup log:", e)

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

    # ⭐ START TEST RESTART LOOP (3 MINUTES)
    loop.create_task(auto_restart_cycle())

    # Keep the bot alive
    await idle()

# -----------------------------------------------------------
# CLEANUP (only runs if NOT SystemExit restart)
# -----------------------------------------------------------
async def cleanup():
    try: await server.cleanup()
    except: pass

    try: await FileStream.stop()
    except: pass

# -----------------------------------------------------------
# MAIN BLOCK — SKIP CLEANUP ON SCHEDULED RESTART
# -----------------------------------------------------------
if __name__ == "__main__":
    try:
        loop.run_until_complete(start_services())
    except SystemExit:
        print("[Main] SystemExit received — skipping cleanup (scheduled restart).")
        pass
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.error(traceback.format_exc())
    finally:
        try:
            if FileStream.is_running:
                loop.run_until_complete(cleanup())
        except:
            pass

        loop.stop()
        print("------------------------ Stopped Services ------------------------")
