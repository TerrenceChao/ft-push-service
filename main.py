import os
import asyncio
from mangum import Mangum
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from src.infra.socket.socket_server import *
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


# @app.websocket('/ws/{room_id}')
# async def websocket_endpoint(websocket: WebSocket, room_id: str):
#     await websocket.accept()
#     await sio.enter_room(websocket, room_id)
#     log.info('Client connected: {sid}, {environ}, {auth}')
#     while True:
#         data = await websocket.receive_json()
#         await sio.emit('receive_messages', data, room=room_id)

# @app.websocket('/')
# async def websocket_endpoint(websocket: WebSocket, room_id: str):
#     await websocket.accept()
#     await sio.enter_room(websocket, room_id)
#     while True:
#         data = await websocket.receive_text()
#         await sio.emit('chat_message', data, room=room_id)


@app.on_event('shutdown')
async def shutdown_event():
    # 在这里执行清理操作，比如关闭数据库连接
    log.info('\n\nCleaning up before Lambda shutdown...\n\n')
    await cancel_all_tasks()
    await shutdown_services()


mount_path = '/'
app.mount(mount_path, sio_app)
app.add_route(mount_path, route=sio_app, methods=['GET', 'POST'])
app.add_websocket_route(mount_path, sio_app)

handler = Mangum(app)
