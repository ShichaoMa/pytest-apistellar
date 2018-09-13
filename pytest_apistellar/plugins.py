import os
import time
import pytest
import threading

from functools import partial
from toolkit import free_port
from apistellar import Application

from .utils import run_server

from .patcher import PropPatcher, EnvPatcher


@pytest.fixture(scope="session")
def join_root_dir(pytestconfig):
    return partial(os.path.join, os.path.abspath(pytestconfig.getoption("rootdir") or "."))


@pytest.fixture(scope="module")
def create_server():
    def run(app):
        port = free_port()
        container = []
        th = threading.Thread(
            target=run_server,
            args=(app, container),
            kwargs={"port": port})
        th.setDaemon(True)
        th.start()
        while not container:
            time.sleep(0.1)
        return port, container[0], container[1]
    return run


@pytest.fixture(scope="module")
def server_port(create_server, request):
    old_path = os.getcwd()
    loop = None
    server = None
    try:
        path = os.path.dirname(request.module.__file__)
        app = Application("test", current_dir=path)
        port, loop, server = create_server(app)
        yield port
    finally:
        os.chdir(old_path)
        if server:
            server.close()
        if loop:
            loop.stop()


@pytest.fixture(scope="session")
def session_env_mock(pytestconfig):
    yield from EnvPatcher.from_config(pytestconfig).process()


@pytest.fixture(scope="module")
def module_env_mock(request):
    yield from EnvPatcher.from_request(request).process()


@pytest.fixture(scope="class")
def class_env_mock(request):
    yield from EnvPatcher.from_request(request).process()


@pytest.fixture
def function_env_mock(request):
    yield from EnvPatcher.from_request(request).process()


@pytest.fixture(scope="session")
def session_prop_mock(pytestconfig, session_env_mock):
    yield from PropPatcher.from_config(pytestconfig).process()


@pytest.fixture(scope="module")
def module_prop_mock(request, module_env_mock):
    yield from PropPatcher.from_request(request).process()


@pytest.fixture(scope="class")
def class_prop_mock(request, class_env_mock):
    yield from PropPatcher.from_request(request).process()


@pytest.fixture
def function_prop_mock(request,
                       session_prop_mock,
                       module_prop_mock,
                       class_prop_mock,
                       function_env_mock):
    yield from PropPatcher.from_request(request).process()


@pytest.fixture
def mock(function_prop_mock):
    """封装monkey patch实现mock env和prop"""
