from fastapi import WebSocket
from ..domains.data.models import *
from ..domains.data.user_data_service import UserDataService
from ..domains.message.connection_manager import ConnectionManager
from ..configs.constants import *
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


class UserMessageService:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        user_data_service: UserDataService,
    ):
        self.manager = connection_manager
        self.user_service = user_data_service

    def user_id(self, role: str, role_id: int):
        return f'{role}:{role_id}'

    async def connect(
        self,
        user: UserDTO,
        websocket: WebSocket,
    ):
        user_id = user.user_id()
        await self.manager.connect(user_id, websocket)
        # data = await websocket.receive_json()
        history_msgs = \
            await self.user_service.get_history_msgs(user.role, user.role_id)
        await self.manager.send_json(
            {
                'msg': f'Welcome! {user.role_id}',
                'notify': history_msgs,  # read from DB
                'mode': 'off-line (read from db)',
            },
            user_id,
            websocket,
        )

    async def messaging(
        self,
        user: UserDTO,
        websocket: WebSocket,
    ):
        user_id = user.user_id()
        data = await self.manager.receive_json(websocket)
        if data.pop('action', None) == 'read':
            await self.user_service.msg_read(user.role, user.role_id, data)
            await self.manager.send_json(
                {
                    'msg': f'Msg: [???] read by {user.role_id}',
                    'data': data.get('payload', None),
                    'mode': 'on-line (real-time msg, db ack)',
                },
                user_id,
                websocket,
            )
        # if ... then ...
        # if ... then ...

    def disconnect(self, websocket: WebSocket):
        self.manager.disconnect(websocket)

    # receive message from message queue
    async def message_consumer(self, msg_body):
        role = msg_body.get(ROLE, None)
        role_id = msg_body.get(ROLE_ID, None)
        user_id = self.user_id(role, role_id)
        mode = msg_body.get(MODE, None)
        if mode == OFFLINE:
            await self.manager.leave_room(user_id)
            log.info(f'message_consumer >> role_id: {role_id} leave room')
            return

        await self.manager.send_json(
            {
                'msg': f'Welcome! {role_id}',
                'notify': [msg_body],
                'mode': 'on-line (real-time msg from message queue)',
            },
            user_id,
        )

        # TODO: 千萬別在"廣播"模式下寫入 DB, 會有很多重複的操作!!!
        # => RabbitMQ: fanout, 或 Kakfa: no group
        # => 廣播

        # TODO: 什麼情況下可寫入 DB? 用"至多消費一次"模式
        # => RabbitMQ: direct, 或 Kakfa: group
        # => 個人訂閱
        await self.user_service.batch_write_items(msg_body)  # write to DB
