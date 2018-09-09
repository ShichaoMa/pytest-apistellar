import os
import time
import pytest
import asyncio
import threading

from toolkit import free_port
from apistellar import Application
from _pytest.monkeypatch import MonkeyPatch
from uvicorn.main import Server, HttpToolsProtocol

from .parser import Parser


def run_server(app, container, port=8080):
    """
    创建一个简单的server用来测试
    :param app:
    :param port:
    :return:
    """
    loop = asyncio.new_event_loop()
    protocol_class = HttpToolsProtocol

    server = Server(app, "127.0.0.1", port, loop, None, protocol_class)
    loop.run_until_complete(server.create_server())
    if server.server is not None:
        container.append(loop)
        container.append(server.server)
        loop.create_task(server.tick())
        loop.run_forever()


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
def parser(pytestconfig):
    return Parser(pytestconfig.inicfg.get("mock_config_file") or "mock.json")


@pytest.fixture(scope="session")
def session_mock(pytestconfig, parser: Parser):
    mocks = pytestconfig.inicfg.get("session_mock")
    if mocks:
        mocks = mocks.strip().split("\n")
    mpatch = MonkeyPatch()
    try:
        process_mocks(mocks, mpatch, parser)
        yield mpatch
    finally:
        mpatch.undo()


@pytest.fixture(scope="module")
def module_mock(request, parser: Parser):
    mocks = getattr(request.module, "MOCKS", None)
    mpatch = MonkeyPatch()
    try:
        process_mocks(mocks, mpatch, parser)
        yield mpatch
    finally:
        mpatch.undo()


@pytest.fixture(scope="class")
def class_mock(request, parser: Parser):
    mocks = getattr(request.cls, "MOCKS", None)
    mpatch = MonkeyPatch()
    try:
        process_mocks(mocks, mpatch, parser)
        yield mpatch
    finally:
        mpatch.undo()


def process_mocks(mocks, monkeypatch, parser):
    if mocks:
        for mock in parser.find_mock(*mocks):
            try:
                old = getattr(mock.obj, mock.name)
                if not callable(old):
                    mock.callable = False
                if asyncio.iscoroutinefunction(old):
                    mock.async = True
            except AttributeError:
                raise RuntimeError(f"{mock.obj} has not attr: {mock.name}")
            monkeypatch.setattr(*mock)


@pytest.fixture
def mock(request, parser: Parser, monkeypatch, module_mock, class_mock):
    """
    mock信息配置在mock.json中，从四个维度加载mock信息
    :param request:
    :param parser:
    :param monkeypatch:
    :param module_mock: 只是为了加载module mock
    :param class_mock: 只是为了加载cls mock
    :return:
    """
    mock_info = getattr(request.function, "mock", None)
    if mock_info:
        process_mocks(mock_info.args, monkeypatch, parser)
