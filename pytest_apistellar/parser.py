# -*- coding:utf-8 -*-
import re
import traceback

from .utils import load


class Attr(object):
    pass


class Prop(object):

    def __init__(self, obj, _name, args, ret_val=None, ret_factory=None, **kwargs):
        """
        :param obj: 被mock的属性拥有者
        :param _name: 被mock的属性名称
        :param ret_val: mock的返回值
        :param ret_factory: mock的返回值生产工厂
        :param asyncable: 被mock的是属性是否是异步的
        :param callable: 被mock的属性是否是可调用的
        :param kwargs: mark传入的kwargs参数
        """
        self.obj = obj
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
        try:
            yield self.obj
            yield self.name
            if self.callable:
                yield self
            else:
                if self.ret_factory:
                    self.ret_val = self.ret_factory()
                yield self.ret_val
        except Exception as e:
            traceback.print_exc()
            raise e

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
        kwargs = self.__dict__.copy()
        # 有可能还没asyncable, callable这两个属性，因为这两个属性是在process_mark时赋予的。
        kwargs.setdefault("asyncable", False)
        kwargs.setdefault("callable", False)
        return "<Prop(name={name} obj={obj} asyncable={asyncable} " \
               "callable={callable} kwargs={kwargs} ret_val={ret_val} " \
               "ret_factory={ret_factory})>".format(**self.__dict__)

    __repr__ = __str__


def parse(mock, args, kwargs=None, regex=re.compile(r" no[\w\s]+?(['\"])(\w+)\1")):
    """
    将mark转换成prop
    :param mock:
    :param args:
    :param kwargs:
    :param regex: 祖先不存在时用来mock祖先，使用一个正则来将祖先的名称找出
    :return:
    """

    obj_name, _, prop = mock.rpartition(".")

    while True:
        try:
            obj = load(obj_name)
            yield Prop(obj, prop, args, **kwargs)
            break
        except AttributeError as ex:
            ancestor = regex.search(str(ex)).group(2)
            _obj_name, last = re.split(ancestor, obj_name, 1)

            for mock_prop in parse(_obj_name + ancestor, tuple(), {"ret_val": Attr()}):
                yield mock_prop
