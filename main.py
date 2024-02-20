import os
import asyncio
from mangum import Mangum
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
)
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
# PREFIX_V1 = '/push/api/v1'
# app.include_router(ws.router, prefix=PREFIX_V1)


@app.websocket('/message')
async def websocket_endpoint(
    websocket: WebSocket,
):
    try:
        user = await user_msg_service.connect(websocket)
        while True:
            await user_msg_service.messaging(user, websocket)

    except WebSocketDisconnect as e:
        log.error('我要斷線啦 WebSocketDisconnect %s', e)
        user_msg_service.disconnect(websocket)


@app.on_event('startup')
async def startup_event():
    async_task(
        subscribe_broadcast_messages,
        'sub_broadcast_task',
    )
    
    async_task(
        subscribe_unicast_messages,
        'sub_unicast_task',
    )

    async_task(
        period_flush,
        'period_flush_task',
    )

    async_task(
        broadcast_message_consumer,
        'broadcast_task',
    )
    
    async_task(
        unicast_message_consumer,
        'unicast_task',
    )


@app.on_event('shutdown')
async def shutdown_event():
    # 在这里执行清理操作，比如关闭数据库连接
    log.info('\n\nCleaning up before Lambda shutdown...\n\n')
    await cancel_all_tasks()
    await shutdown_services()


handler = Mangum(app)
