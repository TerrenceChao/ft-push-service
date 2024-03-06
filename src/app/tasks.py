import asyncio
from typing import Set, Coroutine
from ..configs.conf import *
from ..domains.subscribe.subscribe_service import SubscribeService
from ..domains.message.connection_manager import _connection_manager
from ..domains.data.user_data_service import _user_data_service
from .user_message_service import UserMessageService
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


local_broadcast_queue = asyncio.Queue()
local_unicast_queue = asyncio.Queue()

broadcast_subscriber = SubscribeService()
unicast_subscriber = SubscribeService()

# 訂閱者-廣播訊息 (event='receive_msgs')
async def subscribe_broadcast_messages():
    await broadcast_subscriber.receive_messages(
        local_broadcast_queue,
        BROADCAST_QUEUE,
    )


# 訂閱者-單播訊息 (event='receive_msgs')
async def subscribe_unicast_messages():
    await unicast_subscriber.receive_messages(
        local_unicast_queue,
        UNICAST_QUEUE,
    )


# 定期將 local memory 的資料寫入 DB
async def period_flush():
    while True:
        await asyncio.sleep(FLUSH_DURATION)
        await _user_data_service.flush()


# 消費者
async def message_consumer(
    local_queue: asyncio.Queue,
    consumer_callback: Coroutine,
):
    while True:
        message = await local_queue.get()
        await consumer_callback(message)
        local_queue.task_done()


user_msg_service = UserMessageService(
    _connection_manager,
    _user_data_service
)


# 消費者-廣播訊息 給相同訂閱頻道的所有用戶
async def broadcast_message_consumer():
    await message_consumer(
        local_broadcast_queue,
        user_msg_service.broadcast_message,
    )


# 消費者-單播訊息 短期儲存用戶訊息
async def unicast_message_consumer():
    await message_consumer(
        local_unicast_queue,
        user_msg_service.short_term_storage_of_data,
    )


created_async_tasks: Set[asyncio.Task] = set()


def async_task(task: Coroutine, task_name: str):
    task: asyncio.Task = asyncio.create_task(
        task()
    )
    task.set_name(task_name)
    created_async_tasks.add(task)


async def cancel_all_tasks():
    for async_task in created_async_tasks:
        try:
            if not async_task.cancelled():
                async_task.cancel()
                await async_task
        except asyncio.CancelledError as e:
            log.error('async_task_cancelled error, %s', e)

        finally:
            log.info('async_task_cancelled, %s', async_task.get_name())


async def shutdown_services():
    await _user_data_service.flush()
