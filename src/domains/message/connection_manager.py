import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
from ...configs.conf import WS_JSON_MODE
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


class ConnectionManager:

    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.active_connections: Dict[WebSocket, str] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = room_id
        if not (room_id in self.rooms.keys()):
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        room_id = self.active_connections.get(websocket, None)
        if room_id != None:
            room_connections = self.get_room_connections(room_id)
            room_connections.remove(websocket)
            if len(room_connections) == 0:
                del self.rooms[room_id]

    def get_room_connections(self, room_id: str) -> (Set[WebSocket]):
        return self.rooms.get(room_id, set())

    async def send_json(self, room_id: str, message: Dict):
        if not room_id in self.rooms.keys():
            return

        for connection in self.rooms[room_id]:
            await connection.send_json(message, mode=WS_JSON_MODE)

    async def broadcast_json(self, message: Dict):
        for room_connections in self.rooms.values():
            for connection in room_connections:
                await connection.send_json(message, mode=WS_JSON_MODE)


_connection_manager = ConnectionManager()
