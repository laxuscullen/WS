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
    await broadcast.connect()

async def shutdown_stuff():
    await broadcast.disconnect()

class RoomChatWebsocket(WebSocketEndpoint):
    encoding = "json"

    async def on_connect(self, websocket: WebSocket):
        await websocket.accept()

        room_id = websocket.query_params['room_id']
        websocket.room_id = room_id

        messages = red.lrange(f"room_chat_{room_id}", 0, -1)

        if not messages:
            red.expire(f"room_chat_{room_id}", red_expiry)

        join_message = {
            "user": {
                
                "room_id": room_id,
                "is_system": 1
            },
            "message_data": {
                "text": f"@ has joined the room!",
            }
        }
        
        red.lpush(f"room_chat_{room_id}", orjson.dumps(join_message).decode('utf-8'))

        messages = red.lrange(f"room_chat_{room_id}", 0, 100)
        data = [orjson.loads(message) for message in messages]
        
        # tell everyone someone joined
        await broadcast.publish(channel=f"room_{room_id}", message=orjson.dumps(join_message).decode('utf-8'))

        # send chat data to newly joined member
        await websocket.send_json(data)

        # handle subscriptions using anyio and broadcaster
        async with anyio.create_task_group() as task_group:
            # Receiver Task
            async def receiver():
                await self.on_message_received(websocket=websocket)
                task_group.cancel_scope.cancel()
            
            task_group.start_soon(receiver)
            task_group.start_soon(self.sender, websocket)

    async def sender(self, websocket):
        async with broadcast.subscribe(channel=f"room_{websocket.room_id}") as subscriber:
            async for event in subscriber:
                await websocket.send_json(orjson.loads(event.message))

    async def on_message_received(self, websocket: WebSocket):
        room_id = websocket.room_id

        async for data in websocket.iter_json():

            chat_data = {
                "user": {
                    
                    "room_id": room_id,
                    "is_system": 0
                },
                "message_data": {
                    "text": data['text'],
                }
            }

            chat_data = orjson.dumps(chat_data).decode('utf-8')
            red.lpush(f"room_chat_{room_id}", chat_data)

            # Publish the message to the broadcast channel
            await broadcast.publish(channel=f"room_{room_id}", message=chat_data)
        
    async def on_disconnect(self, websocket: WebSocket, close_code: int):
        room_id = websocket.room_id

        leave_message = {
            "user": {
                
                "room_id": room_id,
                "is_system": 1,
            },
            "message_data": {
                "text": f"@ has left the room :(",
            }
            
        }
        red.lpush(f"room_chat_{room_id}", orjson.dumps(leave_message))

        # Publish the leave message to the broadcast channel
        await broadcast.publish(channel=f"room_{room_id}", message=orjson.dumps(leave_message).decode('utf-8'))
        print(f"Disconnected: {websocket}")

# all the routes
routes = [
    WebSocketRoute("/roomChat", RoomChatWebsocket),
]  # Example [Route("/path", HandlerFunction)], every created route needs to be added here
