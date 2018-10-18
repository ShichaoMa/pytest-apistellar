# -*- coding:utf-8 -*-
import os
import time
import pytest

from functools import partial

from .utils import create_server
from .patcher import build, process


@pytest.fixture(scope="session")
def join_root_dir(pytestconfig):
    return partial(os.path.join, os.path.abspath(
        pytestconfig.getoption("rootdir") or "."))


@pytest.fixture(scope="module")
def server(request):
    old_path = os.getcwd()
    loop = None
    server = None
    try:
        path = os.path.dirname(request.module.__file__)
        loop, server = create_server(path)
        yield server
    finally:
        os.chdir(old_path)
        if server:
            server.server.close()
            server.should_exit = True
            # 等待tick退出
            time.sleep(1)
        if loop:
            loop.stop()


session_mock = build("session", "pytestconfig")
module_mock = build("module")
class_mock = build("class")


@pytest.fixture
def mock(request, session_mock, module_mock, class_mock):
    """封装monkey patch实现mock env和prop"""
    # 这里不能连着写，因为连着写生成器会被马上回收，
    # 回收后会马上调用上下文对象的__exit__，导致触发monkey.undo
    gen = process(request)
    yield next(gen)
