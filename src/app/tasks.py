import asyncio
from typing import Any, Dict, Set, Coroutine
from ..configs.conf import FLUSH_DURATION
from ..domains.subscribe.subscribe_service import _subscribe_service
from ..domains.data.user_data_service import _user_data_service
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


created_async_tasks: Set[asyncio.Task] = set()


async def cancel_all_tasks():
    for async_task in created_async_tasks:
        try:
            if not async_task.cancelled():
                async_task.cancel()
                await async_task
        except asyncio.CancelledError as e:
            log.error('shutdown_event error, %s', e)

        finally:
            log.info('async task cancelled, %s', async_task.get_name())


async def shutdown_services():
    await _user_data_service.flush()

local_queue = asyncio.Queue()


async def subscribe_messages(local_queue: asyncio.Queue):
    while True:
        await _subscribe_service.receive_messages(
            local_queue,
        )
        log.info('subscribe_messages done!')


async def message_consumer(
    local_queue: asyncio.Queue,
    consumer_callback: Coroutine,
):
    while True:
        message = await local_queue.get()
        await consumer_callback(message)
        local_queue.task_done()


async def period_flush():
    while True:
        await asyncio.sleep(FLUSH_DURATION)
        await _user_data_service.flush()


# async def subscribe(sio: AsyncServer, topic: str):
#     while True:
#         await asyncio.sleep(2)  # 每隔 N 秒执行一次，模拟定时任务
#         # 这里编写获取新通知的逻辑
#         # FIXME: 这里的 new_notification 可能有很多?
#         try:
#             role_id, new_notification = _subscribe_service.consume(topic)
#             await sio.emit(
#                 event='receive_msgs',
#                 data={
#                     'msg': f'Welcome! {role_id}',
#                     'notify': [new_notification],
#                     'mode': 'on-line (real-time msg from message queue)',
#                 },
#                 room=role_id,  # 为新通知所在的房间
#             )
#             # TODO: 千萬別在"廣播"模式下寫入 DB, 會有很多重複的操作!!!
#             # => RabbitMQ: fanout, 或 Kakfa: no group
#             # => 廣播

#             # TODO: 什麼情況下可寫入 DB? 用"至多消費一次"模式
#             # => RabbitMQ: direct, 或 Kakfa: group
#             # => 個人訂閱
#             _user_data_service.batch_write_items(new_notification)  # 寫入 DB

#             # 不要急，慢慢來～～～ 寫完 DB 後才 ack
#             _subscribe_service.ack(topic, new_notification)

#         except Exception as e:
#             log.error('consume error, %s', e)


# async def subscribe_v2(sio: AsyncServer, topic: str):
#     queue = asyncio.Queue()
#     await _subscribe_service.consume_task(queue)
#     while True:
#         message = await queue.get()
#         log.info(f"Received message: {message}")
#         role_id = '1234567890'
#         await sio.emit(
#             event='receive_msgs',
#             data={
#                 'msg': f'Welcome! {role_id}',
#                 'notify': [message],
#                 'mode': 'on-line (real-time msg from message queue)',
#             },
#             room=role_id,  # 为新通知所在的房间
#         )
#         # TODO: 什麼情況下可寫入 DB? 用"至多消費一次"模式
#         # => RabbitMQ: direct, 或 Kakfa: group
#         # => 個人訂閱
#         _user_data_service.batch_write_items(message)  # 寫入 DB

#         # # 不要急，慢慢來～～～ 寫完 DB 後才 ack
#         # _subscribe_service.ack(topic, message)
