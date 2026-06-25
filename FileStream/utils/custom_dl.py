import asyncio
import logging

from pyrogram.errors import FloodWait

LOGGER = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 128


class ByteStreamer:

    def __init__(self, client):
        self.client = client

    async def yield_file(
        self,
        file_id,
        index,
        offset,
        first_part_cut,
        last_part_cut,
        part_count,
        chunk_size
    ):

        current_part = 1

        try:

            async for chunk in self.client.stream_media(
                file_id,
                offset=offset
            ):

                if current_part == 1:
                    chunk = chunk[first_part_cut:]

                elif current_part == part_count:
                    chunk = chunk[:last_part_cut]

                current_part += 1

                yield chunk

                await asyncio.sleep(0)

        except FloodWait as e:

            await asyncio.sleep(e.value)

        except:
            pass
