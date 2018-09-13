import asyncio

from functools import partial
from toolkit import load_class as _load


class Prop(object):

    def __init__(self,
                 obj_name,
                 name,
                 *args,
                 ret_val=None,
                 ret_factory=None,
                 async=False,
                 callable=True,
                 **kwargs):
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
        self.args = args or tuple()
        self.kwargs = kwargs or dict()

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
            ret_val = self.ret_factory(
                *args, *self.args, **kwargs, **self.kwargs)
        else:
            ret_val = self.ret_val

        if self.async:
            async def inner():
                if asyncio.iscoroutine(ret_val):
                    await ret_val
                return ret_val
            return inner()
        else:
            return ret_val

    def __str__(self):
        return f"<Prop(name={self.name} " \
               f"obj={self.obj} " \
               f"async={self.async} " \
               f"callable={self.callable} " \
               f"kwargs={self.kwargs} " \
               f"ret_val={self.ret_val} " \
               f"ret_factory={self.ret_factory})>"

    __repr__ = __str__


def parse(mock, args, kwargs=None):
    """
    将mark转换成prop
    :param mock:
    :param args:
    :param kwargs:
    :return:
    """
    obj_name, _, prop = mock.rpartition(".")
    return Prop(obj_name, prop, *args, **kwargs)
