from aiohttp import web

from FileStream.server.stream_routes import media_streamer

routes = web.RouteTableDef()


@routes.get("/watch/{path}")
async def watch_handler(request):

    path = request.match_info["path"]

    return await media_streamer(
        request,
        path
    )


@routes.get("/stream/{path}")
async def stream_handler(request):

    path = request.match_info["path"]

    return await media_streamer(
        request,
        path
    )


def web_server():

    app = web.Application(
        client_max_size=1024**3
    )

    app.router.add_routes(routes)

    return app
