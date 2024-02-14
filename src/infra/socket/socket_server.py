import json
from typing import Coroutine
import asyncio
from socketio import AsyncServer, ASGIApp
from ...app.tasks import *
from ...configs.constants import *
from ...domains.data.data_service import _data_service
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


sio = AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=['*'],
    logger=True,
    engineio_logger=True,
)

sio_app = ASGIApp(
    socketio_server=sio,
    socketio_path='/sockets',
)


async def consumer_callback(msg_body):
    role_id = msg_body.get(ROLE_ID, None)
    mode = msg_body.get(MODE, None)
    if mode == OFFLINE:
        await sio.close_room(role_id)
        log.info(f'consumer_callback >> role_id: {role_id} leave room')
        return

    await sio.emit(
        event='receive_msgs',
        data={
            'msg': f'Welcome! {role_id}',
            'notify': [msg_body],
            'mode': 'on-line (real-time msg from message queue)',
        },
        room=role_id,  # 为新通知所在的房间
    )
    # TODO: 千萬別在"廣播"模式下寫入 DB, 會有很多重複的操作!!!
    # => RabbitMQ: fanout, 或 Kakfa: no group
    # => 廣播

    # TODO: 什麼情況下可寫入 DB? 用"至多消費一次"模式
    # => RabbitMQ: direct, 或 Kakfa: group
    # => 個人訂閱
    await _data_service.batch_write_items(msg_body)


# 即時訊息 (event='receive_msgs')
subscribe_task = asyncio.create_task(
    subscribe_messages(local_queue)
)
subscribe_task.set_name('subscribe_task')
created_async_tasks.add(subscribe_task)

# 啟動本地消息消費者任務
consumer_task = asyncio.create_task(
    message_consumer(local_queue, consumer_callback)
)
consumer_task.set_name('consumer_task')
created_async_tasks.add(consumer_task)

# 定時任務. 定期將 local memory 的資料寫入 DB
period_flush_task = asyncio.create_task(
    period_flush()
)
period_flush_task.set_name('period_flush_task')
created_async_tasks.add(period_flush_task)


@sio.event
async def connect(sid, environ, auth):
    role_id = environ.get(HTTP_ROLE_ID, None)
    role = environ.get(HTTP_ROLE, None)
    log.info(f'Client connected: {sid}, role_id:{role_id}, {auth}')

    # 從 DB 讀取一次性通知  (event='history_msgs')
    history_msgs = _data_service.get_history_msgs(role_id, role)
    await sio.enter_room(sid, role_id)
    await sio.emit(
        event='history_msgs',
        data={
            'msg': f'Welcome! {role_id}',
            'notify': history_msgs,  # read from DB
            'mode': 'off-line (read from db)',
        },
        room=role_id,
    )


@sio.event
async def disconnect(sid):
    log.info(f'Client disconnected: {sid}')


# @sio.on('*', namespace='*')
# async def any_event(event, sid, data):
#     log.info(f'any_event from client {sid}: {data}')

# @sio.on('chat_message')
# async def chat_message(sid, environ):
#     log.info(f'Message from {sid}')
#     await sio.emit('chat_message', 'hello, how are you', sid)


@sio.event
async def message(sid, payload):
    payload = json.loads(payload)
    log.info(f'Message from client {sid}: {payload}')
    log.info(type(payload))

    role_id = payload.get(ROLE_ID, None)
    role = payload.get(ROLE, None)
    mode = payload.get(MODE, None)
    if mode == OFFLINE:
        await sio.close_room(role_id)
        log.info(f'role_id: {role_id} leave room [sid: {sid}]')
        return

    if role_id is None or role is None:
        await sio.emit(
            event='receive_msgs',
            data={'msg': f'no role_id or role found in the request'},
        )
        return

    data = payload.get('data', None)
    if data is None:
        await sio.emit(
            event='receive_msgs',
            data={'msg': f'no data found in the request'},
        )
        return

    # TODO: 'msg read' process...
    # update msg read status in DB
    _data_service.msg_read(role_id, role, data)

    await sio.emit(
        event='receive_msgs',
        data={
            'msg': f'Msg: [???] read by {role_id}',
            'mode': 'on-line (real-time msg, db ack)',
        },
        room=role_id,  # 为新通知所在的房间
    )
