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
        local_queue: asyncio.Queue
    ):
        retry_delay = 1
        max_retry_attempts = 5
        retry_attempt = 0

        async def callback(message: aiormq.abc.DeliveredMessage):
            await self.__consumer_callback(message, mq_channel, local_queue)

        while True:  # 永遠嘗試連線
            if retry_attempt >= max_retry_attempts:
                log.info('Max retry attempts reached, waiting before retrying...')
                await asyncio.sleep(retry_delay)
                retry_attempt = 0  # 重置重試計數器
                continue
            try:
                mq_connect: aiormq.abc.AbstractConnection = \
                    await aiormq.connect(RABBITMQ_URL)
                log.info('receive_messages: connected to RabbitMQ')

                mq_channel: aiormq.abc.AbstractChannel = \
                    await mq_connect.channel()
                await mq_channel.basic_qos(prefetch_count=PREFETCH_SIZE)
                await mq_channel.queue_declare(queue=WORKER_QUEUE, durable=True)
                log.info('receive_messages: declared queue')

                while True:
                    try:
                        await mq_channel.basic_consume(
                            queue=WORKER_QUEUE,
                            consumer_callback=callback,
                            no_ack=False,
                            consumer_tag=self.consumer_tag,
                        )
                        # 保持运行一段时间以接收消息
                        await asyncio.sleep(CONSUME_DURATION)
                        await self.__connect_channel_check(mq_connect, mq_channel)

                    except Exception as e:
                        log.error('An error occurred while subscribing: %s', e)
                        retry_attempt += 1
                        delay = retry_delay * 2**retry_attempt + \
                            random.uniform(-0.5, 0.5)
                        log.warning(f'Retrying in {delay} seconds...')
                        await asyncio.sleep(delay)
                        break

            finally:
                log.warn('\n\n\n receive_messages 任務被強迫取消中\n\n\n')
                await mq_channel.close()
                await mq_connect.close()
                random_delay = random.uniform(0.5, 2.5)
                await asyncio.sleep(random_delay)

        # 关闭连接
        # await mq_channel.close()


_subscribe_service = SubscribeService()
