import sys
import os
import gc
import asyncio
import logging
import traceback
import logging.handlers as handlers

from datetime import datetime, timedelta, timezone

import uvloop
uvloop.install()

from aiohttp import web
from pyrogram import idle

from FileStream.config import Telegram, Server
from FileStream.bot import FileStream
from FileStream.server import web_server
from FileStream.bot.clients import initialize_clients

OWNER_ID = Telegram.OWNER_ID


def fmt_time(dt):
    return dt.strftime("%-d %b %Y | %-I:%M %p")


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

logging.getLogger("aiohttp").setLevel(logging.ERROR)
logging.getLogger("aiohttp.access").setLevel(logging.ERROR)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

server = web.AppRunner(web_server())

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

IST = timezone(timedelta(hours=5, minutes=30))


def cleanup_logs():
    try:
        logs = [
            "streambot.log",
            "streambot.log.1",
            "streambot.log.2"
        ]

        for log in logs:
            if os.path.exists(log):
                os.remove(log)

        print(f"[Cleanup] Removed {log}")

    except Exception as e:
        print(f"[Cleanup Error] {e}")


def get_next_restart():
    now = datetime.now(tz=IST)

    schedule_hours = [3, 9, 15, 21]

    for h in schedule_hours:
        t = now.replace(
            hour=h,
            minute=0,
            second=0,
            microsecond=0
        )

        if t > now:
            return t

    tomorrow = now + timedelta(days=1)

    return tomorrow.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )


async def restart_scheduler():

    while True:

        next_restart = get_next_restart()

        wait_secs = (
            next_restart - datetime.now(tz=IST)
        ).total_seconds()

        print(
            f"[Auto-Restart] Next restart at "
            f"{next_restart.isoformat()} "
            f"({wait_secs / 3600:.2f} hrs)"
        )

        await asyncio.sleep(wait_secs)

        timestamp = fmt_time(datetime.now(tz=IST))

        msg = (
            f"♻️ BOT RESTARTED\n"
            f"⏰ {timestamp}\n"
            f"🔁 Scheduled restart"
        )

        logging.info(msg)
        print(msg)

        try:
            await FileStream.send_message(
                OWNER_ID,
                msg
            )

        except Exception as e:
            print(f"Owner notify failed: {e}")

        cleanup_logs()

        gc.collect()

        try:
            tasks = [
                t for t in asyncio.all_tasks()
                if t is not asyncio.current_task()
            ]

            for task in tasks:
                task.cancel()

        except:
            pass

        try:
            await FileStream.stop()
        except:
            pass

        try:
            await FileStream.session.close()
        except:
            pass

        try:
            await server.cleanup()
        except:
            pass

        print("[Restart] Restarting process...")

        os.execl(
            sys.executable,
            sys.executable,
            *sys.argv
        )


async def start_services():

    print(
        "\n------------------- Starting as Primary Server -------------------\n"
    )

    print(
        "-------------------- Initializing Telegram Bot --------------------"
    )

    await FileStream.start()

    bot_info = await FileStream.get_me()

    FileStream.id = bot_info.id
    FileStream.username = bot_info.username
    FileStream.fname = bot_info.first_name

    print(
        "------------------------------ DONE ------------------------------\n"
    )

    try:

        timestamp = fmt_time(
            datetime.now(tz=IST)
        )

        start_msg = (
            f"🚀 BOT STARTED\n"
            f"⏰ {timestamp}\n"
            f"📌 Reason: Deploy / Restart"
        )

        await FileStream.send_message(
            OWNER_ID,
            start_msg
        )

        print("[Startup] Owner notified.")

    except:
        print("[Startup] Notify failed.")

    print(
        "---------------------- Initializing Clients ----------------------"
    )

    await initialize_clients()

    print(
        "------------------------------ DONE ------------------------------\n"
    )

    print(
        "--------------------- Initializing Web Server ---------------------"
    )

    await server.setup()

    await web.TCPSite(
        server,
        Server.BIND_ADDRESS,
        Server.PORT
    ).start()

    print(
        "------------------------------ DONE ------------------------------\n"
    )

    print(
        "------------------------- Service Started -------------------------"
    )

    print("bot =>>", bot_info.first_name)

    if bot_info.dc_id:
        print("DC ID =>>", bot_info.dc_id)

    print("URL =>>", Server.URL)

    print(
        "------------------------------------------------------------------"
    )

    loop.create_task(restart_scheduler())

    await idle()


async def cleanup():

    try:
        await server.cleanup()
    except:
        pass

    try:
        await FileStream.stop()
    except:
        pass


if __name__ == "__main__":

    try:

        loop.run_until_complete(
            start_services()
        )

    except SystemExit:

        print("[Main] Restart requested.")

    except Exception:

        logging.error(
            traceback.format_exc()
        )

    finally:

        try:
            loop.run_until_complete(
                cleanup()
            )

        except:
            pass

        loop.stop()

        print(
            "------------------------ Stopped Services ------------------------"
        )
