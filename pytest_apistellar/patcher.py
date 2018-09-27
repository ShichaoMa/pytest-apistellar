# -*- coding:utf-8 -*-
import six
import inspect

from abc import ABCMeta, abstractmethod

from _pytest.mark import Mark
from _pytest.monkeypatch import MonkeyPatch

from .parser import parse


class MarkerWrapper(object):
    """
    Mark类__eq__使用(name, args, kwargs)是否相同来判断，
    无法满足去重的要求，所以使用这个类来包装一下使用id来去重。
    """
    def __init__(self, marker):
        self.marker = marker

    def __eq__(self, other):
        return id(self.marker) == id(other)


@six.add_metaclass(ABCMeta)
class Patcher(object):

    @property
    @abstractmethod
    def name(self):
        """
        定义一个名字
        :return:
        """

    @property
    @abstractmethod
    def total_markers(self):
        """
        由于iter_markers会返回所有scope下的mark，
        所以使用这个属性来保证每个markers只处理一次，
        type: list
        :return:
        """

    def __init__(self, markers):
        self.monkey_patch = MonkeyPatch()
        self.markers = markers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monkey_patch.undo()

    def process(self):
        for mark in self.markers:
            if MarkerWrapper(mark) not in self.total_markers:
                self.process_mark(mark)
                self.total_markers.append(mark)

    @abstractmethod
    def process_mark(self, mark):
        """
        个性化定制mark处理方法
        :return:
        """

    @classmethod
    @abstractmethod
    def config_parse(cls, mark):
        """
        config解析方式
        :param mark:
        :return: Mark
        """

    @classmethod
    def from_pytestconfig(cls, pytestconfig):
        mocks = pytestconfig.inicfg.get(cls.name)
        if mocks:
            ms = (cls.config_parse(m) for m in mocks.strip().split("\n"))
        else:
            ms = []
        return cls(ms)

    @classmethod
    def from_request(cls, request, *args, **kwargs):
        return cls(request.node.iter_markers(cls.name))


class PropPatcher(Patcher):
    """
    用来monkey patch 属性
    """
    name = "prop"
    total_markers = list()

    def guess_attr(self, prop, old, mock, func):
        # 证明old是prop
        if hasattr(old, prop):
            setattr(mock, prop, getattr(old, prop))
        # 如果手动指定了，则使用手动指定的
        elif hasattr(mock, prop):
            pass
        # 否则，判定
        else:
            setattr(mock, prop, func(old))

    def process_mark(self, mark):
        mock = parse(mark.args[0], mark.args[1:], kwargs=mark.kwargs)
        try:
            old = getattr(mock.obj, mock.name)
            try:
                from asyncio import iscoroutinefunction
                self.guess_attr("asyncable", old, mock, iscoroutinefunction)
            except ImportError:
                pass
            self.guess_attr("callable", old, mock, callable)
            # apistellar的依赖注入需要return 的signature
            if mock.callable:
                if getattr(old, "__annotations__", None):
                    if old.__annotations__["return"]:
                        mock.__signature__ = inspect.Signature(
                            return_annotation=old.__annotations__["return"])
                        mock.__annotations__ = {
                            "return": old.__annotations__["return"]}
        except AttributeError:
            raise RuntimeError("{} has not attr: {}".format(mock.obj, mock.name))
        self.monkey_patch.setattr(*mock)

    @classmethod
    def config_parse(cls, mark):
        if "->" in mark:
            mark, ret_factory = mark.split("->", 1)
            kwargs = {"ret_factory": ret_factory}
        else:
            mark, ret_val = mark.split("=", 1)
            kwargs = {"ret_val": mark}

        return Mark(cls.name, tuple([mark]), kwargs)


class EnvPatcher(Patcher):
    """
    用来monkey patch 环境变量
    """
    name = "env"
    total_markers = list()

    def process_mark(self, mark):
        prepend = mark.kwargs.pop("prepend", None)
        for key, val in mark.kwargs.items():
            self.monkey_patch.setenv(key, val, prepend)

    @classmethod
    def config_parse(cls, mark):
        key, val = mark.split("=", 1)
        return Mark(cls.name, tuple(), {key: val})
