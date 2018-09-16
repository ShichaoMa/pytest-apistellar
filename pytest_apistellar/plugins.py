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


@pytest.fixture(scope="session")
def session_mock(pytestconfig):
    with EnvPatcher.from_config(pytestconfig) as ep, \
            PropPatcher.from_config(pytestconfig) as pp:
        ep.process()
        pp.process()
        yield


def request_process(request):
    with EnvPatcher.from_request(request) as ep, \
            PropPatcher.from_request(request) as pp:
        ep.process()
        pp.process()
        yield


@pytest.fixture
def mock(request, session_mock, package_mock, module_mock, class_mock):
    """封装monkey patch实现mock env和prop"""
    # 这里不能连着写，因为连着写生成器会被马上回收，
    # 回收后会马上调用上下文对象的__exit__，导致触发monkey.undo，下同
    gen = request_process(request)
    yield next(gen)


@pytest.fixture(scope="package")
def package_mock(request):
    gen = request_process(request)
    yield next(gen)


@pytest.fixture(scope="module")
def module_mock(request):
    gen = request_process(request)
    yield next(gen)


@pytest.fixture(scope="class")
def class_mock(request):
    gen = request_process(request)
    yield next(gen)
