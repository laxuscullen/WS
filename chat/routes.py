from sqlalchemy import func, or_, and_
from datetime import datetime
from starlette.background import BackgroundTask, BackgroundTasks
import asyncio
import anyio
import redis
from redis.commands.json.path import Path
from broadcaster import Broadcast
from sqlalchemy import desc, asc, distinct
from starlette.requests import Request
from starlette.endpoints import HTTPEndpoint, WebSocketEndpoint
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.responses import JSONResponse, RedirectResponse, FileResponse
from starlette.routing import Route, WebSocketRoute
from urllib.parse import quote, unquote
import secrets
# from chat.database import ()
# from chat.utils import ()
import hashlib
from urllib.parse import unquote
# from chat.tokens import token
import json, time, orjson, os

red = redis.Redis(host="localhost", password=os.environ['REDIS_PASS'], port=6379, decode_responses=True)
red_expiry = 60 * 60 * 5 # 5 hours
broadcast = Broadcast(f"redis://:{os.environ['REDIS_PASS']}@localhost:6379")

async def startup_stuff():
    # await broadcast.connect()
    pass

async def shutdown_stuff():
    # await broadcast.disconnect()
    pass

class RoomChatWebsocket(WebSocketEndpoint):
    encoding = "json"

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({})

        async def sender():
            while True:
                await asyncio.sleep(1)

        async def on_message_received(websocket: WebSocket):
            async for data in websocket.iter_json():
                print("------------ got message", data)

        async with anyio.create_task_group() as task_group:

            async def receiver():
                await on_message_received(websocket)
                task_group.cancel_scope.cancel()

            task_group.start_soon(receiver)
            task_group.start_soon(sender)

    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        print(f"Disconnected: {websocket}")

# all the routes
routes = [
    WebSocketRoute("/roomChat", RoomChatWebsocket),
]  # Example [Route("/path", HandlerFunction)], every created route needs to be added here
