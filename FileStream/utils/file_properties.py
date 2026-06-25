import logging

from pyrogram.file_id import FileId

LOGGER = logging.getLogger(__name__)


async def get_file_ids(
    client,
    message_id,
    multi_clients,
    message=None
):

    try:

        file_info = await client.get_messages(
            chat_id=message.chat.id,
            message_ids=message_id
        )

        media = (
            file_info.document
            or file_info.video
            or file_info.audio
            or file_info.voice
            or file_info.video_note
            or file_info.animation
            or file_info.photo
        )

        return media

    except Exception as e:

        LOGGER.exception(e)

        return None


def get_file_info(message):

    media = (
        message.document
        or message.video
        or message.audio
        or message.voice
        or message.video_note
        or message.animation
        or message.photo
    )

    if not media:
        return None

    file_name = getattr(
        media,
        "file_name",
        None
    )

    if not file_name:
        file_name = f"{media.file_unique_id}.bin"

    return {
        "file_id": media.file_id,
        "file_unique_id": media.file_unique_id,
        "file_name": file_name,
        "file_size": media.file_size,
        "mime_type": media.mime_type,
    }
