import asyncio
import logging
import math
import time

from aiohttp import web
from pyrogram.errors import FloodWait

from FileStream.server.exceptions import InvalidHash
from FileStream.server.streamer import FileStreamer
from FileStream.utils.custom_dl import ByteStreamer

LOGGER = logging.getLogger(__name__)

# LIMIT CONCURRENT STREAMS
STREAM_SEMAPHORE = asyncio.Semaphore(15)

class_cache = {}

work_loads = {}


async def media_streamer(
    request: web.Request,
    db_id: str
):

    async with STREAM_SEMAPHORE:

        range_header = request.headers.get(
            "Range",
            None
        )

        # PREVENT EMPTY DICT CRASH
        if not work_loads:
            work_loads[0] = 0

        index = min(
            work_loads,
            key=work_loads.get
        )

        faster_client = work_loads[index]

        tg_connect = class_cache.get(index)

        if tg_connect is None:

            tg_connect = ByteStreamer(
                faster_client
            )

            class_cache[index] = tg_connect

        try:

            file_id = await tg_connect.get_file_properties(
                db_id
            )

        except InvalidHash:

            LOGGER.info(
                "Invalid hash"
            )

            raise web.HTTPForbidden

        except Exception as e:

            LOGGER.exception(e)

            raise web.HTTPInternalServerError

        file_size = file_id.file_size

        if range_header:

            from_bytes, until_bytes = (
                range_header
                .replace("bytes=", "")
                .split("-")
            )

            from_bytes = int(from_bytes)

            until_bytes = (
                int(until_bytes)
                if until_bytes
                else file_size - 1
            )

        else:

            from_bytes = 0
            until_bytes = file_size - 1

        if from_bytes > file_size:

            return web.Response(
                status=416,
                text="Requested Range Not Satisfiable"
            )

        req_length = (
            until_bytes - from_bytes
        )

        # SMALLER CHUNK SIZE
        new_chunk_size = 1024 * 128

        chunk_size = min(
            new_chunk_size,
            req_length
        )

        offset = from_bytes - (
            from_bytes % chunk_size
        )

        first_part_cut = (
            from_bytes - offset
        )

        last_part_cut = (
            until_bytes % chunk_size
        ) + 1

        req_length = (
            until_bytes
            - from_bytes
            + 1
        )

        headers = {
            "Content-Type": file_id.mime_type,
            "Accept-Ranges": "bytes",
            "Content-Length": str(req_length),
            "Content-Range": (
                f"bytes "
                f"{from_bytes}-"
                f"{until_bytes}/"
                f"{file_size}"
            ),
            "Content-Disposition": (
                f'inline; '
                f'filename="{file_id.file_name}"'
            ),
        }

        response = web.StreamResponse(
            status=206 if range_header else 200,
            headers=headers
        )

        await response.prepare(request)

        await response.drain()

        part_count = math.ceil(
            (until_bytes - offset)
            / chunk_size
        )

        body = tg_connect.yield_file(
            file_id,
            index,
            offset,
            first_part_cut,
            last_part_cut,
            part_count,
            chunk_size
        )

        # SAFE WORKLOAD INIT
        work_loads.setdefault(index, 0)

        work_loads[index] += 1

        try:

            async for chunk in body:

                try:

                    await response.write(chunk)

                    # PREVENT EVENT LOOP BLOCKING
                    await asyncio.sleep(0)

                except (
                    ConnectionResetError,
                    BrokenPipeError
                ):

                    LOGGER.warning(
                        "Client disconnected"
                    )

                    break

        except FloodWait as e:

            LOGGER.warning(
                f"FloodWait: {e.value}"
            )

            await asyncio.sleep(
                e.value
            )

        except asyncio.CancelledError:

            LOGGER.warning(
                "Stream cancelled"
            )

        except Exception as e:

            LOGGER.exception(e)

        finally:

            work_loads[index] -= 1

            try:
                await response.write_eof()
            except:
                pass

        return response
