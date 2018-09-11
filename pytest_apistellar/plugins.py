import os
import json
import yaml
import time
import pytest
import inspect
import asyncio
import threading

from functools import partial
from toolkit import free_port
from _pytest.mark import Mark
from apistellar import Application
from _pytest.monkeypatch import MonkeyPatch
from uvicorn.main import Server, HttpToolsProtocol

from .parser import Parser


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


def pytest_addoption(parser):
    parser.addoption("--mock-config-file", action="store",  help="测试地址.")


@pytest.fixture(scope="session")
def join_root_dir(pytestconfig):
    return partial(os.path.join, pytestconfig.getoption("rootdir") or ".")


@pytest.fixture(scope="session")
def parser(pytestconfig):
    config_file = pytestconfig.getoption("mock_config_file") or "mock.json"
    file = open(config_file)
    if config_file[-4:] == "yaml":
        meta = yaml.load(file)
    else:
        meta = json.load(file)
    return Parser(meta)


@pytest.fixture(scope="session")
def session_mock(request, pytestconfig, parser: Parser):
    mocks = pytestconfig.inicfg.get("mock")
    if mocks:
        markers = (Mark("mock", (m,), {}) for m in mocks.strip().split("\n"))
    else:
        markers = []
    yield from monkey_patch(markers, parser)


@pytest.fixture(scope="module")
def module_mock(request, parser: Parser):
    markers = request.node.iter_markers("mock")
    yield from monkey_patch(markers, parser)


@pytest.fixture(scope="class")
def class_mock(request, parser: Parser):
    markers = request.node.iter_markers("mock")
    yield from monkey_patch(markers, parser)


@pytest.fixture
def mock(request, parser: Parser, module_mock, class_mock, session_mock):
    """
    mock信息配置在mock.json中，从四个维度加载mock信息
    :param request:
    :param parser:
    :param monkeypatch:
    :param module_mock: 只是为了加载module mock
    :param class_mock: 只是为了加载cls mock
    :param session_mock 只是为了加载session_mock
    :return:
    """
    markers = request.node.iter_markers("mock")
    yield from monkey_patch(markers, parser)


def run_server(app, container, port=8080):
    """
    创建一个简单的server用来测试
    :param app:
    :param port:
    :return:
    """
    loop = asyncio.new_event_loop()
    server = Server(app, "127.0.0.1", port, loop, None, HttpToolsProtocol)
    loop.run_until_complete(server.create_server())

    if server.server is not None:
        container.append(loop)
        container.append(server.server)
        loop.create_task(server.tick())
        loop.run_forever()


def monkey_patch(markers, parser):
    mpatch = MonkeyPatch()
    try:
        for mark in markers:
            for mock in parser.find_mock(*mark.args, kwargs=mark.kwargs):
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
                                    return_annotation=old.__annotations__["return"])
                                mock.__annotations__ = {"return": old.__annotations__["return"]}

                except AttributeError:
                    raise RuntimeError(f"{mock.obj} has not attr: {mock.name}")
                mpatch.setattr(*mock)

        yield mpatch
    finally:
        mpatch.undo()
