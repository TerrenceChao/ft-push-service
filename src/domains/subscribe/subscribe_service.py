import json
import uuid
import random
import asyncio
import aiormq
from ...configs.conf import *
from ...configs.rabbitmq import RabbitMQConnection, RabbitMQChannel
import logging as log


log.basicConfig(filemode='w', level=log.INFO)


class SubscribeService:
    def __init__(self):
        self.consumer_tag = str(uuid.uuid4())

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
        async with RabbitMQConnection(RABBITMQ_URL) as mq_connect:
            async with RabbitMQChannel(mq_connect) as mq_channel:
                await mq_channel.basic_qos(prefetch_count=PREFETCH_SIZE)
                await mq_channel.queue_declare(queue=queue_name, durable=True)
                log.info(
                    f'receive_messages: connected to RabbitMQ. queue: {queue_name}')

                async def callback(message: aiormq.abc.DeliveredMessage):
                    if mq_channel is None:
                        raise Exception(
                            f'RabbitMQ channel is None. queue: {queue_name}')

                    await self.__consumer_callback(message, mq_channel, local_queue)

                await mq_channel.basic_consume(
                    queue=queue_name,
                    consumer_callback=callback,
                    no_ack=False,
                    consumer_tag=self.consumer_tag,
                )
                while True:
                    log.info('receive_messages: waiting for messages...')
                    await asyncio.sleep(CONSUME_DURATION)
