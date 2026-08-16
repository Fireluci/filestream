import time
import math
import logging
import mimetypes
import traceback
import asyncio
import re
from aiohttp import web
from aiohttp.http_exceptions import BadStatusLine
from FileStream.bot import multi_clients, work_loads, FileStream
from FileStream.config import Telegram, Server
from FileStream.server.exceptions import FIleNotFound, InvalidHash
from FileStream import utils, StartTime, __version__
from FileStream.utils.render_template import render_page

routes = web.RouteTableDef()

@routes.get("/")
async def root_route_handler(request):
    return web.Response(text="Bot is running!")

@routes.get("/status", allow_head=True)
async def status_route_handler(_):
    return web.json_response(
        {
            "server_status": "running",
            "uptime": utils.get_readable_time(time.time() - StartTime),
            "telegram_bot": "@" + FileStream.username,
            "connected_bots": len(multi_clients),
            "loads": dict(
                ("bot" + str(c + 1), l)
                for c, (_, l) in enumerate(
                    sorted(work_loads.items(), key=lambda x: x[1], reverse=True)
                )
            ),
            "version": __version__,
        }
    )

@routes.get("/watch/{path}", allow_head=True)
async def watch_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        return web.Response(text=await render_page(path), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass

# Add this cache dictionary near the top of your file with your other caches (like class_cache)
mediainfo_cache = {}

@routes.get("/mediainfo/{path}", allow_head=True)
async def mediainfo_route_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        
        # Check if MediaInfo is already cached in memory for instant loading
        if path in mediainfo_cache:
            raw_info = mediainfo_cache[path]
        else:
            local_url = f"http://127.0.0.1:{Server.PORT}/dl/{path}"
            
            proc = await asyncio.create_subprocess_exec(
                "mediainfo",
                local_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode == 0 and stdout:
                raw_info = stdout.decode("utf-8", errors="ignore")
                mediainfo_cache[path] = raw_info  # Save to cache
            else:
                raw_info = "Unable to extract MediaInfo."

        # --- CLEANING THE RAW REPORT ---
        lines = []
        for line in raw_info.splitlines():
            stripped = line.strip()
            if stripped.startswith("Title") or stripped.startswith("Movie name"):
                continue
            if stripped.startswith("Text #") or stripped == "Text":
                line = line.replace("Text", "Subtitle")
            lines.append(line)
        cleaned_info = "\n".join(lines)

        # --- DYNAMIC EXTRACTION FOR QUICK SUMMARY ---
        def extract(pattern, text, default="N/A"):
            match = re.search(pattern, text)
            return match.group(1).strip() if match else default

        file_size = extract(r"File size\s*:\s*(.*)", raw_info)
        duration = extract(r"Duration\s*:\s*(.*)", raw_info)
        bitrate = extract(r"Overall bit rate\s*:\s*(.*)", raw_info)
        
        v_width = extract(r"Width\s*:\s*([\d\s]+pixels)", raw_info).replace(" ", "").replace("pixels", "")
        v_height = extract(r"Height\s*:\s*([\d\s]+pixels)", raw_info).replace(" ", "").replace("pixels", "")
        resolution = f"{v_width}x{v_height}" if v_width != "N/A" else "N/A"
        
        video_block_match = re.search(r"Video\n(.*?)(?=\n\n|\nAudio|\nSubtitle|\nText|\Z)", raw_info, re.DOTALL)
        video_block = video_block_match.group(1) if video_block_match else raw_info
        video_codec = extract(r"Format\s*:\s*(.*)", video_block, "AVC / HEVC")

        audio_langs = re.findall(r"Audio\s*#?\d*\n(?:[^\n]+\n)*?.*?Language\s*:\s*(.*)", raw_info)
        if not audio_langs:
            audio_langs = re.findall(r"Language\s*:\s*(.*)", raw_info)
        valid_audio = [l.strip() for l in audio_langs if l.strip().lower() not in ['default', 'forced', 'no']]
        audio_str = ", ".join(dict.fromkeys(valid_audio)) if valid_audio else "None"

        sub_langs = re.findall(r"Subtitle\s*#?\d*\n(?:[^\n]+\n)*?.*?Language\s*:\s*(.*)", raw_info)
        if not sub_langs:
            sub_langs = re.findall(r"Text\s*#?\d*\n(?:[^\n]+\n)*?.*?Language\s*:\s*(.*)", raw_info)
        valid_subs = [l.strip() for l in sub_langs if l.strip().lower() not in ['default', 'forced', 'no']]
        sub_str = ", ".join(dict.fromkeys(valid_subs)) if valid_subs else "None"

        display_filename = "Media File"
        try:
            from FileStream.utils.database import Database
            from FileStream.config import Telegram
            db = Database(Telegram.DATABASE_URL, Telegram.SESSION_NAME)
            file_info = await db.get_file(path)
            if file_info and 'file_name' in file_info:
                raw_name = file_info['file_name']
                step1 = re.sub(r'@[a-zA-Z0-9_]+', '', raw_name)
                step2 = re.sub(r'[^a-zA-Z0-9\s]', ' ', step1)
                display_filename = re.sub(r'\s+', ' ', step2).strip()
        except Exception:
            pass

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MediaInfo Report</title>
            <style>
                body {{
                    background: #0d1117;
                    color: #c9d1d9;
                    font-family: 'Courier New', Courier, monospace;
                    padding: 20px;
                    margin: 0;
                }}
                .file-header {{
                    background: #161b22;
                    border: 1px solid #30363d;
                    padding: 12px 18px;
                    border-radius: 8px;
                    margin-bottom: 15px;
                    font-size: 15px;
                    color: #58a6ff;
                    font-weight: bold;
                }}
                .summary-card {{
                    background: #161b22;
                    border: 1px solid #30363d;
                    border-left: 5px solid #58a6ff;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 25px;
                }}
                .summary-card h3 {{
                    margin-top: 0;
                    color: #58a6ff;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 12px;
                    font-size: 14px;
                }}
                .tag-video {{ color: #3fb950; font-weight: bold; }}
                .tag-audio {{ color: #f0883e; font-weight: bold; }}
                .tag-sub {{ color: #bc8cff; font-weight: bold; }}
                .tag-gen {{ color: #58a6ff; font-weight: bold; }}

                h2 {{
                    color: #58a6ff;
                    border-bottom: 2px solid #30363d;
                    padding-bottom: 10px;
                }}
                pre {{
                    background: #161b22;
                    padding: 20px;
                    border-radius: 12px;
                    overflow-x: auto;
                    white-space: pre-wrap;
                    border: 1px solid #30363d;
                    font-size: 13px;
                    line-height: 1.5;
                    color: #e6edf3;
                }}
            </style>
        </head>
        <body>
            <div class="file-header">
                🔆 [ {file_size} ] {display_filename}
            </div>

            <div class="summary-card">
                <h3>⚡ Quick Media Summary</h3>
                <div class="summary-grid">
                    <div>🎬 <b>Resolution:</b> <span class="tag-video">{resolution}</span></div>
                    <div>🎞️ <b>Video Codec:</b> <span class="tag-video">{video_codec}</span></div>
                    <div>⏱️ <b>Duration:</b> <span class="tag-gen">{duration}</span></div>
                    <div>📦 <b>File Size:</b> <span class="tag-gen">{file_size}</span></div>
                    <div>📊 <b>Bitdepth:</b> <span class="tag-gen">{bitdepth}</span></div>
                    <div>🔊 <b>Audio Tracks:</b> <span class="tag-audio">{audio_str}</span></div>
                    <div>💬 <b>Subtitles:</b> <span class="tag-sub">{sub_str}</span></div>
                </div>
            </div>

            <h2>📄 Full Technical Metadata</h2>
            <pre><code>{cleaned_info}</code></pre>
        </body>
        </html>
        """
        return web.Response(text=html, content_type="text/html")
    except Exception as e:
        return web.Response(text=f"Error generating MediaInfo: {str(e)}", status=500)
        
@routes.get("/dl/{path}", allow_head=True)
async def dl_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        return await media_streamer(request, path)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError, asyncio.CancelledError):
        pass
    except Exception as e:
        traceback.print_exc()
        logging.critical(e.with_traceback(None))
        logging.debug(traceback.format_exc())
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, db_id: str):
    range_header = request.headers.get("Range", "")
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if Telegram.MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.headers.get('X-FORWARDED-FOR', request.remote)}")

    try:
        if not faster_client.is_connected:
            logging.warning(f"Client {index} was disconnected. Reconnecting automatically...")
            await faster_client.start()
    except Exception as e:
        logging.error(f"Failed to reconnect client {index}: {e}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
    else:
        tg_connect = utils.ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
        
    try:
        file_id = await tg_connect.get_file_properties(db_id, multi_clients)
    except Exception as e:
        logging.warning(f"Encountered error with client {index}, clearing cache and refreshing: {e}")
        if faster_client in class_cache:
            del class_cache[faster_client]
        tg_connect = utils.ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
        file_id = await tg_connect.get_file_properties(db_id, multi_clients)
        
    file_size = file_id.file_size

    if range_header:
        try:
            from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        except ValueError:
            from_bytes = request.http_range.start or 0
            until_bytes = (request.http_range.stop or file_size) - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes >= file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = utils.get_name(file_id)
    
    disposition = "attachment" if request.path.startswith("/dl/") else "inline"

    if not mime_type:
        mime_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"

    response = web.StreamResponse(
        status=206 if range_header else 200,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
            "Connection": "keep-alive",
        },
    )

    await response.prepare(request)

    try:
        async for chunk in body:
            await response.write(chunk)
    except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
        logging.info(f"Stream aborted: client closed connection for {file_name}")
    except Exception as e:
        logging.error(f"Error while writing response chunk for {file_name}: {e}")
    finally:
        await response.write_eof()

    return response
