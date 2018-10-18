# -*- coding:utf-8 -*-
import time
import socket
import warnings
import threading


def run_server(path, container, port=None):
    """
    创建一个简单的server用来测试
    :param path:
    :param port:
    :return:
    """
    try:
        import asyncio
        from apistellar import Application
        from uvicorn.main import Server, HttpToolsProtocol
    except ImportError:
        warnings.warn("Python3.6: apistellar required. ")
        raise
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = Application("test", current_dir=path)
    port = port or free_port()
    server = Server(app, "127.0.0.1", port, loop, None, HttpToolsProtocol)
    loop.run_until_complete(server.create_server())

    if server.server is not None:
        container.append(loop)
        container.append(server)
        loop.create_task(server.tick())
        loop.run_forever()


def create_server(path):
    container = []
    th = threading.Thread(target=run_server, args=(path, container))
    th.setDaemon(True)
    th.start()
    while len(container) < 2:
        time.sleep(0.1)
    return container


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


def load(prop_str):
    """
    返回字符串表示的模块、函数、类、若类的属性等
    :param prop_str: module1.class.function....
    :return: function
    """
    attr_list = []
    # 每次循环将prop_str当模块路径查找，成功则返回，
    # 失败则将模块路径回退一级，将回退的部分转换成属性
    # 至到加载模块成功后依次从模块中提取属性。
    ex = None

    while prop_str:
        try:
            obj = __import__(prop_str, fromlist=prop_str.split(".")[-1])
            for attr in attr_list:
                obj = getattr(obj, attr)
            return obj
        except (AttributeError, ImportError) as e:
            prop_str, _sep, attr_str = prop_str.rpartition('.')
            attr_list.insert(0, attr_str)
            ex = e
    else:
        raise ex
