# -*- coding:utf-8 -*-
from _pytest.mark import MarkDecorator, Mark


__version__ = "0.1.0"


class DecoratorProxy(object):
    """
    代理MarkDecorator，重载了其__call__方法，对prop_name和ret_factory进行前缀拼接操作。
    """
    def __init__(self, mock_obj_prefix, mock_factory_prefix, decorator):
        self.decorator = decorator
        self.mock_obj_prefix = mock_obj_prefix
        self.mock_factory_prefix = mock_factory_prefix

    def __call__(self, prop_name, *args, **kwargs):
        ret_factory = kwargs.pop("ret_factory", None)

        if self.mock_obj_prefix:
            pn = "{}.{}".format(self.mock_obj_prefix, prop_name)
        else:
            pn = prop_name

        if ret_factory and isinstance(ret_factory, str) and self.mock_factory_prefix:
            fn = "{}.{}".format(self.mock_factory_prefix, ret_factory)
        else:
            fn = ret_factory
        return self.decorator(pn, *args, ret_factory=fn, **kwargs)

    def __getattr__(self, item):
        return getattr(self.decorator, item)


def prop_alias(mock_obj_prefix=None, mock_factory_prefix="factories"):
    """
    prop mark装饰器别名，指定要mock对象及工厂对象名字的前缀，减少装饰器长度。
    :param mock_obj_prefix:
    :param mock_factory_prefix:
    :return:
    """
    return DecoratorProxy(mock_obj_prefix,
                          mock_factory_prefix,
                          MarkDecorator(Mark("prop", (), {})))
