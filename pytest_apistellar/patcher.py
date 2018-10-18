# -*- coding:utf-8 -*-
import re
import os
import six
import pytest
import inspect

from abc import ABCMeta, abstractmethod

from _pytest.mark import Mark
from _pytest.monkeypatch import MonkeyPatch

from .utils import load
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
        ms = list()
        if mocks:
            for m in mocks.strip().split("\n"):
                if m.strip():
                    mark = cls.config_parse(m.strip())
                    if mark:
                        ms.append(mark)
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


class ItemPatcher(Patcher):
    """
    用来monkey patch Item
    """
    name = "item"
    total_markers = list()
    mark_config_regex = re.compile(r"(.+?)\[(.+?)\]\s*=\s*?(.+)")

    def process_mark(self, mark):
        for key, val in mark.kwargs.items():
            item = mark.args[0]
            if isinstance(item, str):
                item = load(item)
            self.monkey_patch.setitem(item, key, val)

    @classmethod
    def config_parse(cls, mark_str):
        mth = cls.mark_config_regex.search(mark_str)
        if mth:
            prop_name, key, val = mth.groups()
            return Mark(cls.name, tuple([prop_name]), {eval(key): eval(val)})


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
    def config_parse(cls, mark_str):
        key, val = mark_str.split("=", 1)
        return Mark(cls.name, tuple(), {key: val})


class PathPatcher(Patcher):
    """
        用来monkey patch 目录
        """
    name = "path"
    total_markers = list()

    def process_mark(self, mark):
        self.monkey_patch.chdir(mark.args[0])

    @classmethod
    def config_parse(cls, mark_str):
        return Mark(cls.name, tuple([mark_str]), dict())


class SysPathPatcher(PathPatcher):
    """
        用来monkey patch sys path
        """
    name = "syspath"
    total_markers = list()

    def process_mark(self, mark):
        self.monkey_patch.syspath_prepend(os.path.abspath(mark.args[0]))


def process(request, load_from="request"):
    with getattr(PathPatcher, "from_%s" % load_from)(request) as path_patcher,\
         getattr(SysPathPatcher, "from_%s" % load_from)(request) as syspath_patcher,\
         getattr(EnvPatcher, "from_%s" % load_from)(request) as env_patcher,\
         getattr(ItemPatcher, "from_%s" % load_from)(request) as item_patcher,\
         getattr(PropPatcher, "from_%s" % load_from)(request) as prop_petcher:
        path_patcher.process()
        syspath_patcher.process()
        env_patcher.process()
        item_patcher.process()
        prop_petcher.process()
        yield


def build(scope, load_from="request"):
    def mock(request, pytestconfig):
        gen = process(locals()[load_from], load_from=load_from)
        yield next(gen)

    return pytest.fixture(scope=scope, name="%s_mock" % scope)(mock)