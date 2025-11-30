from __future__ import annotations
import logging
from datetime import datetime
from pyrogram import Client
from typing import Any, Optional

from pyrogram.enums import ParseMode, ChatType
from pyrogram.types import Message
from pyrogram.file_id import FileId
from FileStream.bot import FileStream
from FileStream.utils.database import Database
from FileStream.config import Telegram, Server

db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)


async def get_file_ids(client: Client | bool, db_id: str, multi_clients, message) -> Optional[FileId]:
    logging.debug("Starting of get_file_ids")

    # DO NOT FILTER HERE (important for FileStream)
    file_info = await db.get_file(db_id)

    if (not "file_ids" in file_info) or not client:
        logging.debug("Storing file_id of all clients in DB")
        log_msg = await send_file(FileStream, db_id, file_info['file_id'], message)
        await db.update_file_ids(db_id, await update_file_id(log_msg.id, multi_clients))
        logging.debug("Stored file_id of all clients in DB")
        if not client:
            return
        file_info = await db.get_file(db_id)

    file_id_info = file_info.setdefault("file_ids", {})

    if not str(client.id) in file_id_info:
        logging.debug("Storing file_id in DB")
        log_msg = await send_file(FileStream, db_id, file_info['file_id'], message)
        msg = await client.get_messages(Telegram.FLOG_CHANNEL, log_msg.id)
        media = get_media_from_message(msg)
        file_id_info[str(client.id)] = getattr(media, "file_id", "")
        await db.update_file_ids(db_id, file_id_info)
        logging.debug("Stored file_id in DB")

    file_id = FileId.decode(file_id_info[str(client.id)])
    setattr(file_id, "file_size", file_info['file_size'])
    setattr(file_id, "mime_type", file_info['mime_type'])
    setattr(file_id, "file_name", file_info['file_name'])
    setattr(file_id, "unique_id", file_info['file_unique_id'])
    logging.debug("Ending of get_file_ids")

    return file_id


# --------------------------------------------------------
# ONLY VIDEOS + DOCUMENTS ARE VALID FOR USERS
# --------------------------------------------------------
def get_media_from_message(message: "Message") -> Any:
    allowed_media = (
        "video",
        "document"
    )
    for attr in allowed_media:
        media = getattr(message, attr, None)
        if media:
            return media
    return None


def get_media_file_size(m):
    media = get_media_from_message(m)
    return getattr(media, "file_size", "None")


def get_name(media_msg: Message | FileId) -> str:
    if isinstance(media_msg, Message):
        media = get_media_from_message(media_msg)
        file_name = getattr(media, "file_name", "") if media else ""

    elif isinstance(media_msg, FileId):
        file_name = getattr(media_msg, "file_name", "")

    else:
        file_name = ""

    if not file_name:
        media_type = "file"
        ext = ""
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"{media_type}-{date}{ext}"

    return file_name


def get_file_info(message):
    media = get_media_from_message(message)
    if not media:
        return None  # ignore unsupported user uploads

    if message.chat.type == ChatType.PRIVATE:
        user_idx = message.from_user.id
    else:
        user_idx = message.chat.id

    return {
        "user_id": user_idx,
        "file_id": getattr(media, "file_id", ""),
        "file_unique_id": getattr(media, "file_unique_id", ""),
        "file_name": get_name(message),
        "file_size": getattr(media, "file_size", 0),
        "mime_type": getattr(media, "mime_type", "None/unknown")
    }


async def update_file_id(msg_id, multi_clients):
    file_ids = {}
    for client_id, client in multi_clients.items():
        log_msg = await client.get_messages(Telegram.FLOG_CHANNEL, msg_id)
        media = get_media_from_message(log_msg)
        if media:
            file_ids[str(client.id)] = getattr(media, "file_id", "")
    return file_ids


# --------------------------------------------------------
# FIXED send_file() — DOES NOT BLOCK FILESTREAM
# --------------------------------------------------------
async def send_file(client: Client, db_id, file_id: str, message):

    # VERY IMPORTANT → DO NOT FILTER HERE
    # (FileStream internally passes messages that may not contain media)
    
    file_caption = getattr(message, 'caption', None) or get_name(message)

    if message.chat.type == ChatType.PRIVATE:
        uid = message.from_user.id
        name = message.from_user.first_name

        caption_text = (
            f"{file_caption}\n\n"
            f"Requested By : {name} [`{uid}`]\n"
            f"#user{uid}"
        )

    else:
        uid = message.chat.id
        title = message.chat.title

        caption_text = (
            f"{file_caption}\n\n"
            f"Requested By : {title} [`{uid}`]\n"
            f"#user{uid}"
        )

    log_msg = await client.send_cached_media(
        chat_id=Telegram.FLOG_CHANNEL,
        file_id=file_id,
        caption=caption_text,
        parse_mode=ParseMode.MARKDOWN
    )

    return log_msg
