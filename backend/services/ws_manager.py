from typing import Dict
from fastapi import WebSocket
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: int):
        async with self.lock:
            ws = self.active_connections.pop(user_id, None)
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def send_personal_message(self, user_id: int, data: dict):
        async with self.lock:
            ws = self.active_connections.get(user_id)
            if not ws:
                return False
            try:
                await ws.send_text(json.dumps(data, default=str))
                return True
            except Exception:
                # remove broken connection
                self.active_connections.pop(user_id, None)
                return False

    async def broadcast(self, data: dict):
        async with self.lock:
            for user_id, ws in list(self.active_connections.items()):
                try:
                    await ws.send_text(json.dumps(data, default=str))
                except Exception:
                    self.active_connections.pop(user_id, None)


manager = ConnectionManager()

