import inspect
import asyncio

from _pytest.mark import Mark
from abc import ABC, abstractmethod
from _pytest.monkeypatch import MonkeyPatch

count = 0
class Patcher(ABC):

    @property
    @abstractmethod
    def name(self):
        """
        定义一个名字
        :return:
        """

    def __init__(self, markers):
        self.mokey_patch = MonkeyPatch()
        self.markers = markers

    def process(self):
        try:
            for mark in self.markers:
                self.process_mark(mark)
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
    def config_parse(cls, m):
        """
        config解析方式
        :param m:
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
    name = "prop"

    def __init__(self, markers, parser):
        super(PropPatcher, self).__init__(markers)
        self.parser = parser

    def process_mark(self, mark):
        for mock in self.parser.find_mock(*mark.args, kwargs=mark.kwargs):
            try:
                old = getattr(mock.obj, mock.name)
                # or 后面的子句用来防止重复mock
                if asyncio.iscoroutinefunction(old) \
                        or getattr(old, "async", False):
                    mock.async = True
                if not callable(old):
                    mock.callable = False
                else:
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
    def config_parse(cls, m):
        return Mark(cls.name, (m,), {})


class EnvPatcher(Patcher):
    name = "env"

    def process_mark(self, mark):
        prepend = mark.kwargs.pop("prepend", None)
        for key, val in mark.kwargs.items():
            self.mokey_patch.setenv(key, val, prepend)

    @classmethod
    def config_parse(cls, m):
        key, val = m.split("=", 1)
        return Mark(cls.name, tuple(), {key: val})
