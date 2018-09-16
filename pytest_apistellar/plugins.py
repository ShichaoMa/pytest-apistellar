# -*- coding:utf-8 -*-
import os
import pytest

from functools import partial

from .utils import create_server
from .patcher import PropPatcher, EnvPatcher


@pytest.fixture(scope="session")
def join_root_dir(pytestconfig):
    return partial(os.path.join, os.path.abspath(
        pytestconfig.getoption("rootdir") or "."))


@pytest.fixture(scope="module")
def server_port(request):
    old_path = os.getcwd()
    loop = None
    server = None
    try:
        path = os.path.dirname(request.module.__file__)
        port, loop, server = create_server(path)
        yield port
    finally:
        os.chdir(old_path)
        if server:
            server.close()
        if loop:
            loop.stop()


def process(request, load_from="request"):
    with getattr(EnvPatcher, "from_%s" % load_from)(request) as ep, \
            getattr(PropPatcher, "from_%s" % load_from)(request) as pp:
        ep.process()
        pp.process()
        yield


def build(scope, load_from="request"):
    def mock(request, pytestconfig):
        gen = process(locals()[load_from], load_from=load_from)
        yield next(gen)

    return pytest.fixture(scope=scope, name="%s_mock" % scope)(mock)


session_mock = build("session", "pytestconfig")
package_mock = build("package")
module_mock = build("module")
class_mock = build("class")


@pytest.fixture
def mock(request, session_mock, package_mock, module_mock, class_mock):
    """封装monkey patch实现mock env和prop"""
    # 这里不能连着写，因为连着写生成器会被马上回收，
    # 回收后会马上调用上下文对象的__exit__，导致触发monkey.undo
    gen = process(request)
    yield next(gen)
