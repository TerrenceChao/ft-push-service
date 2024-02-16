import os
import asyncio
from mangum import Mangum
from fastapi import (
    FastAPI,
    APIRouter,
    WebSocket, 
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, JSONResponse
from src.domains.data.user_data_service import _user_data_service
from src.domains.message.connection_manager import _connection_manager
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
app.include_router(ws.router, prefix='/push/api/v1')


@app.get('/wakeup')
async def wakeup():
    return JSONResponse(
        content={'msg': 'triggered'},
        status_code=200,
    )

# 定义一个 FastAPI 路由，用于返回包含 HTML 页面的响应


@app.get('/index')
async def get_index():
    return HTMLResponse('''
        <!DOCTYPE html>
        <html>
            <head>
                <title>Socket.IO Test</title>
                <script src='https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.2.0/socket.io.js'></script>
                <script>
                    var socket = io('ws://localhost:8088/sockets');
                    socket.on('connect', function(sid, environ, auth) {
                        console.log('Connected');
                    });
                    socket.on('disconnect', function(sid) {
                        console.log('Disconnected');
                    });
                    function sendMessage() {
                        var message = document.getElementById('message').value;
                        socket.emit('chat_message', message);
                    }
                </script>
            </head>
            <body>
                <h1>Socket.IO Test</h1>
                <input type='text' id='message' placeholder='Enter message'>
                <button onclick='sendMessage()'>Send Message</button>
            </body>
        </html>
    ''')


@app.websocket('/message/{role}/{role_id}')
async def websocket_endpoint(
    role: str,
    role_id: int,
    websocket: WebSocket,
):
    room_id = f'{role}:{role_id}'
    try:
        await _connection_manager.connect(room_id, websocket)
        # verify user (check jwt)
        # data = await websocket.receive_json()
        history_msgs = \
            await _user_data_service.get_history_msgs(role, role_id)
        await _connection_manager.send_json(
            {
                'msg': f'Welcome! {role_id}',
                'notify': history_msgs,  # read from DB
                'mode': 'off-line (read from db)',
            },
            room_id,
            websocket,
        )

        while True:
            data = await _connection_manager.receive_json(websocket)
            if data.pop('action', None) == 'read':
                await _user_data_service.msg_read(role_id, role, data)
                await _connection_manager.send_json(
                    {
                        'msg': f'Msg: [???] read by {role_id}',
                        'data': data.get('payload', None),
                        'mode': 'on-line (real-time msg, db ack)',
                    },
                    room_id,
                    websocket,
                )
            # if ... then ...
            # if ... then ...

    except WebSocketDisconnect as e:
        log.error('我要斷線啦 WebSocketDisconnect %s', e)
        _connection_manager.disconnect(websocket)


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
