import time
from pyrogram import Client
from FileStream.config import Telegram



FileStream = Client(
    "FileStreamBot",
    api_id=Telegram.API_ID,
    api_hash=Telegram.API_HASH,
    bot_token=Telegram.BOT_TOKEN,

    workers=min(Telegram.WORKERS, 10),

    sleep_threshold=30,
    max_concurrent_transmissions=5,

    no_updates=False,

    in_memory=True
)


StartTime = time.time()

__version__ = "2.0"
