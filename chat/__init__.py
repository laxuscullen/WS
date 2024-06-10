from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware

from chat.routes import routes, startup_stuff, shutdown_stuff


middleware = [
    Middleware(GZipMiddleware, minimum_size=1000),
    # Middleware(LimitMiddleware, requests=60, timeout=60, block_for=60)
]
app = Starlette(debug=True, middleware=middleware,
                routes=routes, on_startup=[startup_stuff], on_shutdown=[shutdown_stuff])
