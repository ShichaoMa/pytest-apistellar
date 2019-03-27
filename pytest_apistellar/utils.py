# -*- coding:utf-8 -*-
import re
import time
import socket
import warnings
import threading

from functools import wraps, reduce


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
    # 等待10秒
    for i in range(100):
        time.sleep(0.1)
        if len(container) == 2:
            break
    else:
        raise RuntimeError("子线程启动超时！")
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


def guess(val):
    """
    通过字符串表达式去猜测要返回的值
    @param val:
    @return:
    """
    try:
        return eval(val)
    except NameError:
        # 如果报错了，可能是字符串描述的模块没有导入，则导入模块
        try:
            # 寻找[或(，来判断是否需要执行方法或函数
            mth = re.search(r"[\[\(]", val)
            # 如果存在，则证明需要调用函数或类
            if mth:
                prop_str, args_str = val[:mth.start()], val[mth.start():]
                prop = load(prop_str)
                prop_name = "_local_prop_name"
                locals()[prop_name] = prop
                return eval(prop_name + args_str)
            else:
                return load(val)
        except (ImportError, NameError, AttributeError):
            return val
    except SyntaxError:
        return val


def cache_property(func):
    """
    缓存属性，只计算一次
    :param func:
    :return:
    """
    @property
    @wraps(func)
    def wrapper(*args, **kwargs):
        if func.__name__ not in args[0].__dict__:
            args[0].__dict__[func.__name__] = func(*args, **kwargs)
        return args[0].__dict__[func.__name__]
    return wrapper


class classproperty(object):
    """
    property只能用于实例方法到实例属性的转换，使用classproperty来支持类方法到类属性的转换
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func(owner)


def cache_classproperty(func):
    """
    缓存类属性，只计算一次
    :param func:
    :return:
    """
    @classproperty
    @wraps(func)
    def wrapper(*args, **kwargs):
        prop_name = "_" + func.__name__
        if prop_name not in args[0].__dict__:
            setattr(args[0], prop_name, func(*args, **kwargs))
        return args[0].__dict__[prop_name]
    return wrapper


class MarkerWrapper(object):
    """
    Mark类__eq__使用(name, args, kwargs)是否相同来判断，
    无法满足去重的要求，所以使用这个类来包装一下使用id来去重。
    """
    def __init__(self, marker):
        self.marker = marker

    def __hash__(self):
        return id(self.marker)

    def __eq__(self, other):
        if not hasattr(other, "marker"):
            return False

        return id(self.marker) == id(other.marker)

    def __repr__(self):
        return repr(self.marker)

    __str__ = __repr__


def find_children(cls):
    """
    获取所有(component)的子类或其实例。
    :param cls: 父类
    :return:
    """
    return set(reduce(lambda x, y: x.union(set([y])).union(find_children(y)),
                      cls.__subclasses__(), set()))
