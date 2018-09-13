# -*- coding:utf-8 -*-
import asyncio
from uvicorn.main import Server, HttpToolsProtocol


def run_server(app, container, port=8080):
    """
    创建一个简单的server用来测试
    :param app:
    :param port:
    :return:
    """
    loop = asyncio.new_event_loop()
    server = Server(app, "127.0.0.1", port, loop, None, HttpToolsProtocol)
    loop.run_until_complete(server.create_server())

    if server.server is not None:
        container.append(loop)
        container.append(server.server)
        loop.create_task(server.tick())
        loop.run_forever()
