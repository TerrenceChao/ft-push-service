import asyncio
from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse
from src.configs.constants import *
from src.domains.data.models import *
from src.app.tasks import _user_msg_service
from ..req.validation import websocket_endpoint_check
import logging as log

log.basicConfig(filemode='w', level=log.INFO)

router = APIRouter(
    tags=['WebSocket'],
    # dependencies=[Depends(get_token_header)],
    responses={404: {'description': 'Not found'}},
)


@router.get('/wakeup')
async def wakeup():
    return JSONResponse(
        content={'msg': f'triggered'},
        status_code=200,
    )

# 定义一个 FastAPI 路由，用于返回包含 HTML 页面的响应


@router.get('/index')
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


@router.websocket('/ws/{role}/{role_id}')
async def websocket_endpoint(
    websocket: WebSocket,
    user: UserDTO = Depends(websocket_endpoint_check),
):
    try:
        await _user_msg_service.connect(user, websocket)
        while True:
            await _user_msg_service.messaging(user, websocket)

    except WebSocketDisconnect as e:
        log.error('我要斷線啦 WebSocketDisconnect %s', e)
        _user_msg_service.disconnect(websocket)
