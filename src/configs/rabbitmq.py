import aiormq
import logging as log

log.basicConfig(filemode='w', level=log.INFO)


class RabbitMQConnection:
    def __init__(self, url: str):
        self.url = url
        self.connection = None

    async def __aenter__(self):
        log.info('RabbitMQ connection init...')
        self.connection = await aiormq.connect(self.url)
        log.info('RabbitMQ connection established.')
        return self.connection

    async def __aexit__(self, exc_type, exc, tb):
        log.warn(f'RabbitMQConnection closing...')
        if self.connection:
            await self.connection.close()
            log.warn(f'RabbitMQConnection is closed')


class RabbitMQChannel:
    def __init__(self, connection: aiormq.abc.AbstractConnection):
        self.connection = connection
        self.channel = None

    async def __aenter__(self):
        log.info('RabbitMQ channel init...')
        self.channel = await self.connection.channel()
        log.info('RabbitMQ channel established.')
        return self.channel

    async def __aexit__(self, exc_type, exc, tb):
        log.warn(f'RabbitMQChannel closing...')
        if self.channel:
            await self.channel.close()
            log.warn(f'RabbitMQChannel is closed')
