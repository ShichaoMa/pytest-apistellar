import inspect
import asyncio

from _pytest.mark import Mark
from abc import ABC, abstractmethod
from toolkit import load_function as _load
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


class Patcher(ABC):

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
        self.mokey_patch = MonkeyPatch()
        self.markers = markers

    def process(self):
        try:
            for mark in self.markers:
                if MarkerWrapper(mark) not in self.total_markers:
                    self.process_mark(mark)
                    self.total_markers.append(mark)
            yield self
        finally:
            self.mokey_patch.undo()

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
    def from_config(cls, pytestconfig, *args, **kwargs):
        mocks = pytestconfig.inicfg.get(cls.name)
        if mocks:
            ms = (cls.config_parse(m) for m in mocks.strip().split("\n"))
        else:
            ms = []
        return cls(ms, *args, **kwargs)

    @classmethod
    def from_request(cls, request, *args, **kwargs):
        return cls(request.node.iter_markers(cls.name), *args, **kwargs)


class PropPatcher(Patcher):
    """
    用来monkey patch 属性
    """
    name = "prop"
    total_markers = list()

    def process_mark(self, mark):
        mock = parse(mark.args[0], mark.args[1:], kwargs=mark.kwargs)
        try:
            old = getattr(mock.obj, mock.name)
            # 如果是异步函数或者之前mock过有为true的async属性或者在配置中指定了async=true
            if asyncio.iscoroutinefunction(old) \
                    or getattr(old, "async", False) or\
                    mock.async:
                mock.async = True
            # 证明old是prop
            if hasattr(old, "callable"):
                mock.callable = old.callable
            # 当old不是prop同时也不是可调用对象时
            elif not callable(old):
                mock.callable = False
            # apistellar的依赖注入需要return 的signature
            if mock.callable:
                if getattr(old, "__annotations__", None):
                    if old.__annotations__["return"]:
                        mock.__signature__ = inspect.Signature(
                            return_annotation=old.__annotations__[
                                "return"])
                        mock.__annotations__ = {
                            "return": old.__annotations__[
                                "return"]}
        except AttributeError:
            raise RuntimeError(
                f"{mock.obj} has not attr: {mock.name}")
        self.mokey_patch.setattr(*mock)

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
            self.mokey_patch.setenv(key, val, prepend)

    @classmethod
    def config_parse(cls, mark):
        key, val = mark.split("=", 1)
        return Mark(cls.name, tuple(), {key: val})
