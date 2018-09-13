# -*- coding:utf-8 -*-
import socket


def run_server(app, container, port=8080):
    """
    创建一个简单的server用来测试
    :param app:
    :param port:
    :return:
    """
    import asyncio
    from uvicorn.main import Server, HttpToolsProtocol

    loop = asyncio.new_event_loop()
    server = Server(app, "127.0.0.1", port, loop, None, HttpToolsProtocol)
    loop.run_until_complete(server.create_server())

    if server.server is not None:
        container.append(loop)
        container.append(server.server)
        loop.create_task(server.tick())
        loop.run_forever()


def free_port():
    """
    Determines a free port using sockets.
    """
    free_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    free_socket.bind(('0.0.0.0', 0))
    free_socket.listen(5)
    port = free_socket.getsockname()[1]
    free_socket.close()
    return port


def load_module(module_str):
    """
    返回字符串表示的模块
    :param module_str: os.path
    :return: os.path
    """
    return __import__(module_str, fromlist=module_str.split(".")[-1])


def load_function(function_str):
    """
    返回字符串表示的函数对象
    :param function_str: module1.module2.function
    :return: function
    """

    mod_str, _sep, func_str = function_str.rpartition('.')
    mod = None
    if mod_str:
        try:
            mod = getattr(load_module(mod_str), func_str)
        except AttributeError:
            pass
    if not mod:
        # 可能整体是一个模块
        mod = load_module(function_str)
    return mod