# -*- coding:utf-8 -*-
from pyaop import Proxy, AOP
from _pytest.mark import MarkDecorator, Mark


__version__ = "0.1.6"


def wrapper(mock_obj_prefix, mock_factory_prefix):

    def call(proxy, prop_name, *args, **kwargs):
        ret_factory = kwargs.pop("ret_factory", None)
        if mock_obj_prefix:
            pn = "{}.{}".format(mock_obj_prefix, prop_name)
        else:
            pn = prop_name

        if ret_factory and isinstance(ret_factory, str) and mock_factory_prefix:
            fn = "{}.{}".format(mock_factory_prefix, ret_factory)
        else:
            fn = ret_factory
        kwargs["ret_factory"] = fn
        return (pn, ) + args, kwargs
    return call


def prop_alias(mock_obj_prefix=None, mock_factory_prefix="factories"):
    """
    prop mark装饰器别名，指定要mock对象及工厂对象名字的前缀，减少装饰器长度。
    :param mock_obj_prefix:
    :param mock_factory_prefix:
    :return:
    """
    return Proxy(MarkDecorator(Mark("prop", (), {})),
                 before=[AOP.Hook(
                     wrapper(mock_obj_prefix, mock_factory_prefix),
                     ["__call__"])])
