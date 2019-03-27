# -*- coding:utf-8 -*-
import re
import os
import six
import pytest
import inspect

from functools import partial
from abc import ABCMeta, abstractmethod

from _pytest.mark import Mark
from _pytest.monkeypatch import MonkeyPatch

from .parser import parse
from .utils import load, cache_classproperty, MarkerWrapper, guess, find_children

namespace = {"function": 10, "class": 20, "package": 30, "module": 40, "session": 50}


@six.add_metaclass(ABCMeta)
class Patcher(object):

    @property
    @abstractmethod
    def name(self):
        """
        定义一个名字
        :return:
        """

    @cache_classproperty
    def total_markers(self):
        """
        由于iter_markers会返回所有scope下的mark，
        所以使用这个属性来保证每个markers只处理一次，
        :return:
        :rtype: dict
        """
        return dict()

    def __init__(self, markers):
        self.monkey_patch = MonkeyPatch()
        self.markers = markers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.monkey_patch.undo()

    def process(self, request):
        fixture_kwargs = dict()
        # 只有PropPatcher才需要注入fixture。
        if self.name == "prop":
            for name, fixture in request._fixture_defs.items():
                # 当前请求作用域适用于该fixture的作用域
                if namespace[request.scope] <= namespace[fixture.scope]:
                    fixture_kwargs[name] = request.getfixturevalue(name)

        for mark in self.markers:
            mark_wrapper = MarkerWrapper(mark)
            # 由于当前request可获得的markers包括大于等于当前作用域的所有marker。
            # 而请求加载顺序的作用域从大到小，如到function作用域时，
            # 其它作用域已经处理过一些mark，这些mark需要过滤掉，
            # 但在执行时若使用了多输入的fixture，会出现请求重复发起的情况，
            # 此时需要重复执行mock， 因此，不能对function级别的mark进行过滤。
            if mark_wrapper not in self.total_markers or \
                    self.total_markers[mark_wrapper] == "function":
                self.process_mark(mark, fixture_kwargs)
                self.total_markers[mark_wrapper] = request.scope

    @abstractmethod
    def process_mark(self, mark, fixture_kwargs):
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
    order = 5

    def guess_attr(self, prop, old, mock, func):
        # 证明old是prop
        if hasattr(old, prop):
            setattr(mock, prop, getattr(old, prop))
        # 如果手动指定了，则使用手动指定的
        elif hasattr(mock, prop):
            pass
        # 否则，自行判断
        else:
            setattr(mock, prop, func(old))

    def process_mark(self, mark, fixture_kwargs):
        kwargs = mark.kwargs.copy()
        # 是否往factory中注入fixture
        fixture_inject = kwargs.pop("fixture_inject", False)
        for mock in parse(mark.args[0], mark.args[1:], kwargs=kwargs):
            if mock.ret_factory and fixture_kwargs and fixture_inject:
                mock.ret_factory = partial(mock.ret_factory, **fixture_kwargs)

            try:
                old = getattr(mock.obj, mock.name, None)
                try:
                    from asyncio import iscoroutinefunction
                    self.guess_attr("asyncable", old, mock, iscoroutinefunction)
                except ImportError:
                    mock.asyncable = False
                self.guess_attr("callable", old, mock, callable)
                # apistellar的依赖注入需要return 的signature
                if mock.callable:
                    if getattr(old, "__annotations__", None):
                        if "return" in old.__annotations__:
                            mock.__signature__ = inspect.Signature(
                                return_annotation=old.__annotations__["return"])
                            mock.__annotations__ = {
                                "return": old.__annotations__["return"]}
            except AttributeError:
                raise RuntimeError("{} has not attr: {}".format(
                    mock.obj, mock.name))
            self.monkey_patch.setattr(*mock, raising=False)

    @classmethod
    def config_parse(cls, mark):
        if "->" in mark:
            mark, ret_factory = mark.split("->", 1)
            kwargs = {"ret_factory": ret_factory}
        else:
            mark, ret_val = mark.split("=", 1)
            kwargs = {"ret_val": guess(ret_val)}

        return Mark(cls.name, tuple([mark]), kwargs)


class ItemPatcher(Patcher):
    """
    用来monkey patch Item
    """
    name = "item"
    order = 4
    mark_config_regex = re.compile(r"(.+?)\[(.+?)\]\s*=\s*?(.+)")

    def process_mark(self, mark, fixture_kwargs):
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
            return Mark(cls.name, tuple([prop_name]), {eval(key): guess(val)})


class EnvPatcher(Patcher):
    """
    用来monkey patch 环境变量
    """
    name = "env"
    order = 3

    def process_mark(self, mark, fixture_kwargs):
        prepend = mark.kwargs.pop("prepend", None)
        for key, val in mark.kwargs.items():
            self.monkey_patch.setenv(key, val, prepend)

    @classmethod
    def config_parse(cls, mark_str):
        key, val = mark_str.split("=", 1)
        return Mark(cls.name, tuple(), {key: guess(val)})


class PathPatcher(Patcher):
    """
        用来monkey patch 目录
        """
    name = "path"
    order = 1

    def process_mark(self, mark, fixture_kwargs):
        self.monkey_patch.chdir(mark.args[0])

    @classmethod
    def config_parse(cls, mark_str):
        return Mark(cls.name, tuple([guess(mark_str)]), dict())


class SysPathPatcher(PathPatcher):
    """
    用来monkey patch sys path
    """
    name = "syspath"
    order = 2

    def process_mark(self, mark, fixture_kwargs):
        self.monkey_patch.syspath_prepend(os.path.abspath(mark.args[0]))


def process(fromobj, request=None, load_from="request",
            patchers=sorted(find_children(Patcher), key=lambda x: x.order)):
    if not patchers:
        yield

    patcher = patchers[0]
    with getattr(patcher, "from_%s" % load_from)(fromobj) as patcher:
        patcher.process(request)
        # 使用一个变量来指向生成器，防止在整个函数返回之前被gc
        gen = process(fromobj, request, load_from, patchers[1:])
        yield next(gen)


def build(scope, load_from="request"):
    def mock(request, pytestconfig):
        gen = process(locals()[load_from], request=request, load_from=load_from)
        yield next(gen)

    return pytest.fixture(scope=scope, name="%s_mock" % scope)(mock)