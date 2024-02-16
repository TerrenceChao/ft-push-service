import os
import asyncio
from mangum import Mangum
from fastapi import FastAPI
from src.routers.v1 import ws
from src.app.tasks import *
import logging as log

log.basicConfig(filemode='w', level=log.INFO)

STAGE = os.environ.get('STAGE')
root_path = '/' if not STAGE else f'/{STAGE}'
app = FastAPI(
    title='ForeignTeacher: Push Service',
    root_path=root_path,
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=['*'],
#     allow_credentials=True,
#     allow_methods=['*'],
#     allow_headers=['*'],
# )

# websocket 以此種方式註冊無效
# router_v1 = APIRouter(prefix="/push/api/v1")
# router_v1.include_router(ws.router)

# websocket 以此種方式註冊有效
PREFIX_V1 = '/push/api/v1'
app.include_router(ws.router, prefix=PREFIX_V1)


@app.on_event('startup')
async def startup_event():
    subscribe_task = asyncio.create_task(
        subscribe_messages(local_queue)
    )
    subscribe_task.set_name('subscribe_task')
    created_async_tasks.add(subscribe_task)

    period_flush_task = asyncio.create_task(
        period_flush()
    )
    period_flush_task.set_name('period_flush_task')
    created_async_tasks.add(period_flush_task)

    user_msg_consumer_task = asyncio.create_task(
        user_message_consumer(local_queue)
    )
    user_msg_consumer_task.set_name('user_msg_consumer_task')
    created_async_tasks.add(user_msg_consumer_task)


@app.on_event('shutdown')
async def shutdown_event():
    # 在这里执行清理操作，比如关闭数据库连接
    log.info('\n\nCleaning up before Lambda shutdown...\n\n')
    await cancel_all_tasks()
    await shutdown_services()


handler = Mangum(app)
