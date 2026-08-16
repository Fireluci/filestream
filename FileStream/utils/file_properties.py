from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from pyrogram import Client
from pyrogram.enums import ParseMode, ChatType
from pyrogram.types import Message
from pyrogram.file_id import FileId

from FileStream.bot import FileStream
from FileStream.utils.database import Database
from FileStream.config import Telegram


db = Database(
    Telegram.DATABASE_URL,
    Telegram.SESSION_NAME
)


async def get_file_ids(
    client: Client | bool,
    db_id: str,
    multi_clients,
    message: Optional[Message] = None,
) -> Optional[FileId]:

    logging.debug("Starting of get_file_ids")

    file_info = await db.get_file(db_id)

    if not file_info:
        logging.error(
            f"File information not found for {db_id}"
        )
        return None

    file_id_info = file_info.get("file_ids")

    # --------------------------------------------------------
    # FIRST CALL DURING FILE UPLOAD
    #
    # The real Message object is available here.
    # Copy the file to FLOG_CHANNEL and save its Telegram
    # file IDs in MongoDB.
    # --------------------------------------------------------

    if not file_id_info:

        if message is None:
            logging.error(
                f"Cannot create FLOG file for {db_id}: "
                "original Message is missing"
            )
            return None

        logging.debug(
            f"Sending file {db_id} to FLOG_CHANNEL"
        )

        log_msg = await send_file(
            FileStream,
            db_id,
            file_info["file_id"],
            message,
        )

        file_id_info = await update_file_id(
            log_msg.id,
            multi_clients,
        )

        if not file_id_info:
            logging.error(
                f"No FLOG file IDs generated for {db_id}"
            )
            return None

        await db.update_file_ids(
            db_id,
            file_id_info,
        )

        logging.debug(
            f"Stored FLOG file IDs for {db_id}"
        )

    # --------------------------------------------------------
    # DOWNLOAD / STREAM CALL
    #
    # At this point the FLOG file already exists.
    # Never call send_file() here.
    # --------------------------------------------------------

    if not client:
        return None

    client_id = str(client.id)

    encoded_file_id = file_id_info.get(client_id)

    if not encoded_file_id:
        logging.error(
            f"No FLOG file ID for client {client_id} "
            f"and file {db_id}"
        )
        return None

    try:
        file_id = FileId.decode(encoded_file_id)
    except Exception:
        logging.exception(
            f"Failed decoding FLOG file ID for {db_id}"
        )
        return None

    file_id.file_size = file_info.get(
        "file_size",
        0,
    )

    file_id.mime_type = file_info.get(
        "mime_type",
        "application/octet-stream",
    )

    file_id.file_name = file_info.get(
        "file_name",
        "",
    )

    file_id.unique_id = file_info.get(
        "file_unique_id",
        "",
    )

    logging.debug(
        f"Ending get_file_ids for {db_id}"
    )

    return file_id


# --------------------------------------------------------
# ONLY VIDEOS + DOCUMENTS ARE VALID FOR USERS
# --------------------------------------------------------

def get_media_from_message(message: "Message") -> Any:
    allowed_media = (
        "video",
        "document",
    )

    for attr in allowed_media:
        media = getattr(
            message,
            attr,
            None,
        )

        if media:
            return media

    return None


def get_media_file_size(m):
    media = get_media_from_message(m)

    return getattr(
        media,
        "file_size",
        "None",
    )


def get_name(
    media_msg: Message | FileId
) -> str:

    if isinstance(media_msg, Message):

        media = get_media_from_message(
            media_msg
        )

        file_name = (
            getattr(
                media,
                "file_name",
                "",
            )
            if media
            else ""
        )

    elif isinstance(media_msg, FileId):

        file_name = getattr(
            media_msg,
            "file_name",
            "",
        )

    else:
        file_name = ""

    if not file_name:

        media_type = "file"
        ext = ""

        date = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        file_name = (
            f"{media_type}-{date}{ext}"
        )

    return file_name


def get_file_info(message):

    media = get_media_from_message(
        message
    )

    if not media:
        return None

    if message.chat.type == ChatType.PRIVATE:
        user_idx = message.from_user.id
    else:
        user_idx = message.chat.id

    return {
        "user_id": user_idx,
        "file_id": getattr(
            media,
            "file_id",
            "",
        ),
        "file_unique_id": getattr(
            media,
            "file_unique_id",
            "",
        ),
        "file_name": get_name(message),
        "file_size": getattr(
            media,
            "file_size",
            0,
        ),
        "mime_type": getattr(
            media,
            "mime_type",
            "None/unknown",
        ),
    }


async def update_file_id(
    msg_id,
    multi_clients,
):

    file_ids = {}

    for client_id, client in multi_clients.items():

        log_msg = await client.get_messages(
            Telegram.FLOG_CHANNEL,
            msg_id,
        )

        media = get_media_from_message(
            log_msg
        )

        if media:

            file_ids[str(client.id)] = (
                getattr(
                    media,
                    "file_id",
                    "",
                )
            )

    return file_ids


# --------------------------------------------------------
# SEND FILE TO FLOG_CHANNEL
# --------------------------------------------------------

async def send_file(
    client: Client,
    db_id,
    file_id: str,
    message,
):

    file_caption = (
        getattr(
            message,
            "caption",
            None,
        )
        or get_name(message)
    )

    if message.chat.type == ChatType.PRIVATE:

        uid = message.from_user.id
        name = message.from_user.first_name

        caption_text = (
            f"{file_caption}\n\n"
            f"Requested By : "
            f"[{name}]"
            f"(tg://user?id={uid}) "
            f"[`{uid}`]\n"
            f"#user{uid}"
        )

    else:

        uid = message.chat.id
        title = message.chat.title

        caption_text = (
            f"{file_caption}\n\n"
            f"Requested By : "
            f"[{title}]"
            f"(tg://user?id={uid}) "
            f"[`{uid}`]\n"
            f"#user{uid}"
        )

    log_msg = await client.send_cached_media(
        chat_id=Telegram.FLOG_CHANNEL,
        file_id=file_id,
        caption=caption_text,
        parse_mode=ParseMode.MARKDOWN,
    )

    return log_msg
