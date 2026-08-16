import asyncio
import logging
from typing import Dict, Union

from FileStream.bot import work_loads
from pyrogram import Client, utils, raw
from .file_properties import get_file_ids

from pyrogram.session import Session, Auth
from pyrogram.errors import AuthBytesInvalid, FloodWait
from pyrogram.file_id import (
    FileId,
    FileType,
    ThumbnailSource,
)


class ByteStreamer:

    def __init__(self, client: Client):

        self.clean_timer = 30 * 60
        self.client: Client = client

        self.cached_file_ids: Dict[
            str,
            FileId
        ] = {}

        asyncio.create_task(
            self.clean_cache()
        )


    async def get_file_properties(
        self,
        db_id: str,
        multi_clients
    ) -> FileId:

        """
        Returns the properties of a media file.

        Cached properties are returned immediately.
        Otherwise the stored FLOG file ID is loaded.
        """

        if db_id not in self.cached_file_ids:

            logging.debug(
                "Before Calling generate_file_properties"
            )

            file_id = await self.generate_file_properties(
                db_id,
                multi_clients,
            )

            if file_id is None:
                raise FileNotFoundError(
                    f"No Telegram file ID found for {db_id}"
                )

            logging.debug(
                f"Cached file properties for file with ID {db_id}"
            )

        return self.cached_file_ids[db_id]


    async def generate_file_properties(
        self,
        db_id: str,
        multi_clients
    ) -> FileId:

        """
        Load the already-created FLOG file ID.

        IMPORTANT:
        This function does NOT send anything to FLOG_CHANNEL.
        The upload handler already did that.
        """

        logging.debug(
            "Loading stored FLOG file ID"
        )

        file_id = await get_file_ids(
            self.client,
            db_id,
            multi_clients,
            None,
        )

        if file_id is None:
            raise FileNotFoundError(
                f"FLOG file ID not found for {db_id}"
            )

        self.cached_file_ids[
            db_id
        ] = file_id

        logging.debug(
            f"Generated file ID and Unique ID "
            f"for file with ID {db_id}"
        )

        return file_id


    async def generate_media_session(
        self,
        client: Client,
        file_id: FileId
    ) -> Session:

        """
        Generates the media session for the DC
        that contains the media file.
        """

        media_session = client.media_sessions.get(
            file_id.dc_id,
            None
        )

        if media_session is None:

            if file_id.dc_id != await client.storage.dc_id():

                media_session = Session(
                    client,
                    file_id.dc_id,
                    await Auth(
                        client,
                        file_id.dc_id,
                        await client.storage.test_mode(),
                    ).create(),
                    await client.storage.test_mode(),
                    is_media=True,
                )

                await media_session.start()

                for _ in range(6):

                    exported_auth = await client.invoke(
                        raw.functions.auth.ExportAuthorization(
                            dc_id=file_id.dc_id
                        )
                    )

                    try:

                        await media_session.invoke(
                            raw.functions.auth.ImportAuthorization(
                                id=exported_auth.id,
                                bytes=exported_auth.bytes,
                            )
                        )

                        break

                    except AuthBytesInvalid:

                        logging.debug(
                            f"Invalid authorization bytes "
                            f"for DC {file_id.dc_id}"
                        )

                        continue

                else:

                    await media_session.stop()

                    raise AuthBytesInvalid

            else:

                media_session = Session(
                    client,
                    file_id.dc_id,
                    await client.storage.auth_key(),
                    await client.storage.test_mode(),
                    is_media=True,
                )

                await media_session.start()

            logging.debug(
                f"Created media session for DC "
                f"{file_id.dc_id}"
            )

            client.media_sessions[
                file_id.dc_id
            ] = media_session

        else:

            logging.debug(
                f"Using cached media session for DC "
                f"{file_id.dc_id}"
            )

        return media_session


    @staticmethod
    async def get_location(
        file_id: FileId
    ) -> Union[
        raw.types.InputPhotoFileLocation,
        raw.types.InputDocumentFileLocation,
        raw.types.InputPeerPhotoFileLocation,
    ]:

        file_type = file_id.file_type

        if file_type == FileType.CHAT_PHOTO:

            if file_id.chat_id > 0:

                peer = raw.types.InputPeerUser(
                    user_id=file_id.chat_id,
                    access_hash=file_id.chat_access_hash,
                )

            else:

                if file_id.chat_access_hash == 0:

                    peer = raw.types.InputPeerChat(
                        chat_id=-file_id.chat_id
                    )

                else:

                    peer = raw.types.InputPeerChannel(
                        channel_id=utils.get_channel_id(
                            file_id.chat_id
                        ),
                        access_hash=file_id.chat_access_hash,
                    )

            location = raw.types.InputPeerPhotoFileLocation(
                peer=peer,
                volume_id=file_id.volume_id,
                local_id=file_id.local_id,
                big=(
                    file_id.thumbnail_source
                    == ThumbnailSource.CHAT_PHOTO_BIG
                ),
            )

        elif file_type == FileType.PHOTO:

            location = raw.types.InputPhotoFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )

        else:

            location = raw.types.InputDocumentFileLocation(
                id=file_id.media_id,
                access_hash=file_id.access_hash,
                file_reference=file_id.file_reference,
                thumb_size=file_id.thumbnail_size,
            )

        return location


    async def yield_file(
        self,
        file_id: FileId,
        index: int,
        offset: int,
        first_part_cut: int,
        last_part_cut: int,
        part_count: int,
        chunk_size: int,
    ):

        """
        Custom generator that yields media bytes.
        """

        client = self.client

        work_loads[index] += 1

        logging.debug(
            f"Starting to yield file with client {index}. "
            f"Active workloads: {work_loads[index]}"
        )

        current_part = 1

        try:

            media_session = (
                await self.generate_media_session(
                    client,
                    file_id,
                )
            )

            location = await self.get_location(
                file_id
            )

            r = await media_session.invoke(
                raw.functions.upload.GetFile(
                    location=location,
                    offset=offset,
                    limit=chunk_size,
                ),
            )

            if isinstance(
                r,
                raw.types.upload.File
            ):

                while True:

                    chunk = r.bytes

                    if not chunk:
                        break

                    elif part_count == 1:

                        yield chunk[
                            first_part_cut:last_part_cut
                        ]

                    elif current_part == 1:

                        yield chunk[
                            first_part_cut:
                        ]

                    elif current_part == part_count:

                        yield chunk[
                            :last_part_cut
                        ]

                    else:

                        yield chunk

                    current_part += 1
                    offset += chunk_size

                    if current_part > part_count:
                        break

                    r = await media_session.invoke(
                        raw.functions.upload.GetFile(
                            location=location,
                            offset=offset,
                            limit=chunk_size,
                        ),
                    )

        except (
            asyncio.CancelledError,
            ConnectionResetError,
            BrokenPipeError,
        ):

            logging.info(
                f"Client disconnected early while "
                f"streaming part {current_part}/"
                f"{part_count} on worker {index}."
            )

        except (
            TimeoutError,
            AttributeError,
        ) as e:

            logging.warning(
                f"Streaming error on worker "
                f"{index}: {e}"
            )

        except Exception as e:

            logging.error(
                f"Unexpected exception during "
                f"file streaming on worker "
                f"{index}: {e}"
            )

        finally:

            work_loads[index] = max(
                0,
                work_loads[index] - 1,
            )

            logging.debug(
                f"Finished yielding file on client "
                f"{index}. Remaining workloads: "
                f"{work_loads[index]}"
            )


    async def clean_cache(self) -> None:

        """
        Function to clean the cache.
        """

        while True:

            await asyncio.sleep(
                self.clean_timer
            )

            self.cached_file_ids.clear()

            logging.debug(
                "Cleaned the cache"
            )
