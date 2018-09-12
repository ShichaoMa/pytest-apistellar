import asyncio

from functools import partial
from toolkit import load_class as _load


class Prop(object):

    def __init__(self,
                 obj_name,
                 name,
                 ret_val=None,
                 ret_factory=None,
                 async=False,
                 callable=True,
                 kwargs=None):
        """

        :param obj_name: 被mock的属性拥有者
        :param name: 被mock的属性名称
        :param ret_val: mock的返回值
        :param ret_factory: mock的返回值生产工厂
        :param async: 被mock的是属性是否是异步的
        :param callable: 被mock的属性是否是可调用的
        :param kwargs: mark传入的kwargs参数
        """
        self.obj = _load(obj_name)
        self.name = name
        self.ret_val = ret_val
        self.ret_factory = ret_factory and _load(ret_factory)
        self.async = async
        self.callable = callable
        self.kwargs = kwargs or {}

    def __iter__(self):
        yield self.obj
        yield self.name
        if self.callable:
            yield self
        else:
            if self.ret_factory:
                self.ret_val = self.ret_factory()
            yield self.ret_val

    def __call__(self, *args, **kwargs):
        if self.ret_factory:
            ret_val = self.ret_factory(*args, **kwargs, **self.kwargs)
        else:
            ret_val = self.ret_val

        if self.async:
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            future.set_result(ret_val)
            return future
        else:
            return ret_val


class Object(object):

    def __init__(self, mock):
        self.obj_name = mock["obj"]
        self.elements = set()
        for prop in mock.get("props", []):
            self.elements.add(partial(Prop, self.obj_name, **prop))

    def find(self, obj_name, name):
        if self.obj_name == obj_name:
            for element_cls in self.elements:
                if element_cls.keywords["name"] == name:
                    return element_cls


class Parser(object):

    def __init__(self, meta):
        self.meta = meta
        self.objects = [Object(mock) for mock in self.meta["mocks"]]

    def find_mock(self, *mocks, kwargs=None):
        for mock_name in mocks:
            obj_name, _, prop = mock_name.rpartition(".")

            for obj in self.objects:
                mock_cls = obj.find(obj_name, prop)
                if mock_cls:
                    instance = mock_cls(kwargs=kwargs)
                    # 有一些同步的方式会返回future来冒充异步，需要手动在kwargs中指明
                    if kwargs.get("async"):
                        instance.async = True
                    yield instance
                    break
            else:
                print(f"Mock of {mock_name} not found. ")
