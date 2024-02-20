import asyncio
import json
from pydantic import BaseModel
from typing import Dict, Set, Tuple, Optional
from fastapi import WebSocket
from ...configs.conf import (
    MAX_WS_CONNECTIONS,
    MAX_WS_TTL,
    WS_JSON_MODE,
)
from ...infra.utils.time_utils import *
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


class Record(BaseModel):
    room_id: str = 'default'
    ts: int = 0
    count: int = 0

    def __init__(self, room_id: str):
        super().__init__()
        self.room_id = room_id
        self.ts = current_sec()

    def updated_now(self):
        self.ts = current_sec()
        self.count += 1
        return self


class ConnectionManager:

    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}
        self.connections: Dict[WebSocket, Record] = {}
        # self.active_connections: Dict[WebSocket, Record] = {}
        self.lock = asyncio.Lock()

    async def connect(self, room_id: str, websocket: WebSocket):
        # await websocket.accept()
        self.__connect(room_id, websocket)
        if not (room_id in self.rooms.keys()):
            self.rooms[room_id] = set()
        self.rooms[room_id].add(websocket)

    def disconnect(self, websocket: WebSocket):
        record: Record = self.__disconnect(websocket)
        if record != None:
            room_connections = self.get_room_connections(record.room_id)
            room_connections.remove(websocket)
            if len(room_connections) == 0:
                del self.rooms[record.room_id]

    def get_room_connections(self, room_id: str) -> (Set[WebSocket]):
        return self.rooms.get(room_id, set())

    def __connect(self, room_id: str, websocket: WebSocket):
        record = Record(room_id)
        self.connections[websocket] = record
        # TODO ...

    def __disconnect(self, websocket: WebSocket) -> (Tuple[Record, None]):
        record = self.connections.pop(websocket, None)
        if record == None:
            return None

        # TODO ...
        return record

    def __active(self, websocket: WebSocket = None):
        if websocket == None:
            return

        record = self.connections.get(websocket, None)
        if record != None:
            record.updated_now()

    async def receive_json(self, websocket: WebSocket):
        self.__active(websocket)
        return await websocket.receive_json()

    async def leave_room(self, room_id: str):
        if not room_id in self.rooms.keys():
            return

        for connection in self.rooms[room_id]:
            self.disconnect(connection)
        del self.rooms[room_id]
        log.info(f'leave_room >> room_id: {room_id}')

    async def send_json(self, message: Dict, room_id: str, websocket: WebSocket = None):
        # self.__active(websocket)
        if not room_id in self.rooms.keys():
            return

        for connection in self.rooms[room_id]:
            await connection.send_json(message, mode=WS_JSON_MODE)

    async def broadcast_json(self, message: Dict):
        for room_connections in self.rooms.values():
            for connection in room_connections:
                await connection.send_json(message, mode=WS_JSON_MODE)

    async def aging(self):
        if len(self.connections) < MAX_WS_CONNECTIONS:
            return

        now = current_sec()
        for ws, record in self.connections.items():
            if now - record.ts > MAX_WS_TTL:
                self.disconnect(ws)


_connection_manager = ConnectionManager()
