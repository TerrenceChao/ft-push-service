import os

LOCAL_REGION = os.getenv("LOCAL_REGION", "ap-northeast-1")

# websocket management
MAX_WS_CONNECTIONS = int(os.getenv("MAX_WS_CONNECTIONS", 5000))
MAX_WS_TTL = int(os.getenv("MAX_WS_TTL", 120))
WS_JSON_MODE = os.getenv("WS_JSON_MODE", "text") # text or binary

# message queue
# RabbitMQ
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqps://tjztylpc:1u5UI7W5bQJ0QyYIu5moGBalLvxAqVoc@octopus.rmq3.cloudamqp.com/tjztylpc")
WORKER_QUEUE = os.getenv("WORKER_QUEUE", "push.worker")
CONSUME_DURATION = int(os.getenv("CONSUME_DURATION", "20"))  # default 20 secs
FLUSH_DURATION = int(os.getenv("FLUSH_DURATION", "10"))  # default 10 secs
MAX_BODY_SIZE = int(os.getenv("MAX_BODY_SIZE", 2 * 1024))  # default 2 KB

# DynamoDB
LOCAL_DB = "http://localhost:8000"
DYNAMODB_URL = os.getenv("DYNAMODB_URL", None)


# env params
PREFETCH_SIZE = int(os.getenv("PREFETCH_SIZE", "100"))
