import socketio
import asyncio

# 创建 Socket.IO 客户端
sio = socketio.Client()

# 连接到 Socket.IO 服务器
def connect_to_server():
    sio.connect(
        url = 'http://localhost:8088/sockets',
        # socketio_path='sockets',
        transports=['websocket'],
    )

# 监听来自服务器的消息
@sio.event
def chat_message(data):
    print('Message from server:', data)

# 向服务器发送消息
def send_message(msg):
    sio.emit('chat_message', msg)

# 主函数
def main():
    connect_to_server()
    send_message('Hello from client')
    # asyncio.sleep(2)  # 等待一段时间以接收服务器的响应
    sio.disconnect()

# 运行主函数
if __name__ == "__main__":
    main()
