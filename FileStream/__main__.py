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

logging.basicConfig(
    level=logging.INFO,
    datefmt="%d/%m/%Y %H:%M:%S",
    format='[%(asctime)s] %(levelname)s - %(message)s',
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

        await asyncio.sleep(wait_secs)

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

        os.execl(
            sys.executable,
            sys.executable,
            *sys.argv
        )


async def start_services():

    await FileStream.start()

    bot_info = await FileStream.get_me()

    FileStream.id = bot_info.id

    await initialize_clients()

    await server.setup()

    await web.TCPSite(
        server,
        Server.BIND_ADDRESS,
        Server.PORT
    ).start()

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
