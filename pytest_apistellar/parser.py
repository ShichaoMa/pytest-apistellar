# -*- coding:utf-8 -*-
from .utils import load


class Prop(object):

    def __init__(self,
                 _obj_name,
                 _name,
                 args,
                 ret_val=None,
                 ret_factory=None,
                 **kwargs):
        """

        :param _obj_name: 被mock的属性拥有者
        :param _name: 被mock的属性名称
        :param ret_val: mock的返回值
        :param ret_factory: mock的返回值生产工厂
        :param asyncable: 被mock的是属性是否是异步的
        :param callable: 被mock的属性是否是可调用的
        :param kwargs: mark传入的kwargs参数
        """
        self.obj = load(_obj_name)
        self.name = _name
        self.ret_val = ret_val
        self.ret_factory = load(ret_factory) \
            if isinstance(ret_factory, str) else ret_factory
        # 优先使用手动指定的标志位
        if "asyncable" in kwargs:
            self.asyncable = kwargs.pop("asyncable")
        if "callable" in kwargs:
            self.callable = kwargs.pop("callable")
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
        kwargs.update(self.kwargs)
        if self.ret_factory:
            ret_val = self.ret_factory(*(args + self.args), **kwargs)
        else:
            ret_val = self.ret_val

        if self.asyncable:
            from .compact import get_coroutine
            return get_coroutine(ret_val)
        else:
            return ret_val

    def __str__(self):
        return "<Prop(name={name} obj={obj} asyncable={asyncable} " \
               "callable={callable} kwargs={kwargs} ret_val={ret_val} " \
               "ret_factory={ret_factory})>".format(**self.__dict__)

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
    return Prop(obj_name, prop, args, **kwargs)
