import socketio
import asyncio

# 创建 Socket.IO 客户端
sio_client = socketio.AsyncClient()
sio = socketio.AsyncSimpleClient()


# 连接到 Socket.IO 服务器
url = 'http://localhost:8088'
transports = ['websocket']
async def connect_to_server():
    await sio_client.connect(
        url = url,
        socketio_path='/sockets',
        transports=transports,
    )
    # await sio.connect(url, transports=transports)


@sio_client.event
async def connect(sid, environ, auth):
    print(f'Client connected: {sid}, {environ}, {auth}')
    await sio_client.emit('receive_messages', {'msg': 'Welcome!'})


@sio_client.event
async def disconnect(sid):
    print(f'Client disconnected: {sid}')

# app.mount('/sockets', sio_app)

# 监听来自服务器的消息
@sio_client.event
async def receive_messages(sid, data, auth):
    print('Message from server:', sid)

# 向服务器发送消息
async def send_message(msg):
    await sio_client.emit('receive_messages', msg)

# 主函数
async def main():
    await connect_to_server()
    # event = await sio_client.receive()
    # print(f'received event: "{event[0]}" with arguments {event[1:]}')
    await send_message({
        'msg': 'this is Terrence',
        'user_id': 'this-is-my-user-id'
    })
    await asyncio.sleep(2)  # 等待一段时间以接收服务器的响应
    await sio_client.disconnect()



# 运行主函数
if __name__ == "__main__":
    asyncio.run(main())
