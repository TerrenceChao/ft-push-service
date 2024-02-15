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

    async def consume_task(self, local_queue: asyncio.Queue):
        # 创建通道
        connection: aiormq.abc.AbstractConnection = \
            await aiormq.connect(RABBITMQ_URL)
        channel: aiormq.abc.AbstractChannel = \
            await connection.channel()

        # 声明一个队列
        await channel.queue_declare(queue=WORKER_QUEUE, durable=True)

        # 从队列中获取消息
        async for message in channel.consume(WORKER_QUEUE):
            async with message.process():
                # 将消息放入队列
                await local_queue.put(message.body.decode())

    '''
    subscribe to a topic, from message queue(ex: RabbitMQ, Kafka)
    '''

    # async def consume(self, topic: str) -> (Tuple[int, Dict[str, Any]]):
    #     # read from message queue(ex: RabbitMQ, Kafka)
    #     data = {
    #         'role_id': '1234567890',
    #     }
    #     # role_id 是接收者
    #     role_id = data.get('role_id', None)

    #     return (
    #         role_id,
    #         {
    #             'role_id': role_id,
    #             'title': 'Teacher Eva apply for a job',
    #             'content': {
    #                 'role_id': f'company id: {role_id}',
    #                 'jid': 'job id: 123',
    #                 'tid': 'teacher id',
    #                 'rid': 'resume id: 456',
    #                 'title': 'Job Title',
    #             },
    #             'category': 'notification',
    #             'read': False,
    #         }
    #     )  # 假设这是新通知

    # async def ack(self, topic: str, new_notification: Any):
    #     log.info(f'ack: {topic}')
    #     # 关闭连接
    #     await self.mq_connect.close()

    # async def notify(self, sio: Any, topic: str):
    #     while True:
    #         await asyncio.sleep(2)  # 每隔 N 秒执行一次，模拟定时任务
    #         # 这里编写获取新通知的逻辑
    #         # FIXME: 这里的 new_notification 可能有很多?
    #         role_id, new_notification = self.subscribe(topic)
    #         await sio.emit(
    #             event='receive_msgs',
    #             data={
    #                 'msg': f'Welcome! {role_id}',
    #                 'notify': [new_notification],
    #                 'mode': 'on-line (real-time msg from message queue)',
    #             },
    #             room=role_id,  # 为新通知所在的房间
    #         )
    #         # TODO: 千萬別在"廣播"模式下寫入 DB, 會有很多重複的操作!!!
    #         # => RabbitMQ: fanout, 或 Kakfa: no group
    #         # => 廣播

    #         # TODO: 什麼情況下可寫入 DB? 用"至多消費一次"模式
    #         # => RabbitMQ: direct, 或 Kakfa: group
    #         # => 個人訂閱

    #         # ack = self.mq.ack(new_notification)

    # async def notify(self, sio: Any, topic: str, data: Dict, sid: str):
    #     role_id = data.get('role_id', None)
    #     while True:
    #         await asyncio.sleep(2)  # 每隔 N 秒执行一次，模拟定时任务
    #         # 这里编写获取新通知的逻辑
    #         new_notification = self.subscribe(topic, data, role_id)
    #         await sio.emit(
    #             event='receive_msgs',
    #             data={
    #                 'msg': f'Welcome! {role_id}',
    #                 'notify': [new_notification],
    #                 'mode': 'on-line (real-time msg from message queue)',
    #             },
    #             room=role_id,  # 为新通知所在的房间
    #         )


_subscribe_service = SubscribeService()
