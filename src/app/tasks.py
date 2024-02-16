import asyncio
from typing import Set, Coroutine
from ..configs.conf import FLUSH_DURATION
from ..domains.subscribe.subscribe_service import _subscribe_service
from ..domains.message.connection_manager import _connection_manager
from ..domains.data.user_data_service import _user_data_service
from .user_message_service import UserMessageService
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


# 即時訊息 (event='receive_msgs')
async def subscribe_messages(local_queue: asyncio.Queue):
    while True:
        await _subscribe_service.receive_messages(
            local_queue,
        )


# 定期將 local memory 的資料寫入 DB
async def period_flush():
    while True:
        await asyncio.sleep(FLUSH_DURATION)
        await _user_data_service.flush()


# 訊息消費者
async def message_consumer(
    local_queue: asyncio.Queue,
    consumer_callback: Coroutine,
):
    while True:
        message = await local_queue.get()
        await consumer_callback(message)
        local_queue.task_done()


_user_msg_service = UserMessageService(
    _connection_manager,
    _user_data_service
)


# 個人訊息消費者
async def user_message_consumer(
    local_queue: asyncio.Queue
):
    await message_consumer(
        local_queue,
        _user_msg_service.message_consumer,
    )
