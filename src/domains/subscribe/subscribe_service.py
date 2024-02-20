import json
import uuid
import random
import asyncio
import aiormq
from ...configs.conf import *
import logging as log


log.basicConfig(filemode='w', level=log.INFO)


class SubscribeService:
    def __init__(self):
        self.consumer_tag = str(uuid.uuid4())

    async def __connect_channel_check(
        self,
        mq_connect: aiormq.abc.AbstractConnection,
        mq_channel: aiormq.abc.AbstractChannel,
    ):
        if mq_connect is None or mq_channel is None:
            raise Exception('RabbitMQ connection or channel is None.')

        if not mq_connect.is_closed:
            log.info('RabbitMQ connection is open.')
        else:
            raise Exception('RabbitMQ connection is closed.')

        if not mq_channel.is_closed:
            log.info('RabbitMQ channel is open and active.')
        else:
            raise Exception('RabbitMQ channel is closed or inactive.')

    async def __consumer_callback(
        self,
        message: aiormq.abc.DeliveredMessage,
        mq_channel: aiormq.abc.AbstractChannel,
        local_queue: asyncio.Queue,
    ):
        delivery_tag = message.delivery_tag
        try:
            log.info('Received msg: %s', message)
            msg_body_size = len(message.body)
            if msg_body_size == 0:
                log.warning('Received empty message body, skipping...')
                await mq_channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
                return

            if msg_body_size > MAX_BODY_SIZE:
                log.warning('Received message body is too large, skipping...')
                await mq_channel.basic_nack(delivery_tag=delivery_tag, requeue=False)
                return

            msg_body = json.loads(message.body.decode())
            log.info('Received decoded msg body: %s', msg_body)
            await local_queue.put(msg_body)
            await mq_channel.basic_ack(delivery_tag=delivery_tag)

        except Exception as e:
            log.error('\nAn error occurred while processing message: \n %s', e)
            await mq_channel.basic_nack(delivery_tag=delivery_tag, requeue=False)

    async def receive_messages(
        self,
        local_queue: asyncio.Queue,
        queue_name: str,
    ):
        mq_connect: aiormq.abc.AbstractConnection = None
        mq_channel: aiormq.abc.AbstractChannel = None

        retry_delay = 1
        max_retry_attempts = 5
        retry_attempt = 0

        while True:  # 永遠嘗試連線
            if retry_attempt >= max_retry_attempts:
                log.info('Max retry attempts reached, waiting before retrying...')
                await asyncio.sleep(retry_delay)
                retry_attempt = 0  # 重置重試計數器
                continue
            try:
                mq_connect = await aiormq.connect(RABBITMQ_URL)
                log.info(
                    f'receive_messages: connected to RabbitMQ. queue: {queue_name}')

                mq_channel = await mq_connect.channel()
                await mq_channel.basic_qos(prefetch_count=PREFETCH_SIZE)
                await mq_channel.queue_declare(queue=queue_name, durable=True)
                log.info(f'receive_messages: declared queue: {queue_name}')

                async def callback(message: aiormq.abc.DeliveredMessage):
                    if mq_channel is None:
                        raise Exception(
                            f'RabbitMQ channel is None. queue: {queue_name}')

                    await self.__consumer_callback(message, mq_channel, local_queue)

                while True:
                    try:
                        await mq_channel.basic_consume(
                            queue=BROADCAST_QUEUE,
                            consumer_callback=callback,
                            no_ack=False,
                            consumer_tag=self.consumer_tag,
                        )
                        # 保持运行一段时间以接收消息
                        await asyncio.sleep(CONSUME_DURATION)
                        await self.__connect_channel_check(mq_connect, mq_channel)

                    except Exception as e:
                        log.error(
                            'An error occurred while subscribing: %s, %s', queue_name, e)
                        retry_attempt += 1
                        delay = retry_delay * 2**retry_attempt + \
                            random.uniform(-0.5, 0.5)
                        log.warning(
                            f'Retrying in {delay} seconds...  queue: {queue_name}')
                        await asyncio.sleep(delay)
                        break

            finally:
                log.warn(
                    f'\n\n\n receive_messages 任務被強迫取消中 queue: {queue_name}\n\n\n')
                if mq_channel != None:
                    await mq_channel.close()
                if mq_connect != None:
                    await mq_connect.close()
