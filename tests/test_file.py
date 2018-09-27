######为了发现在当前目录下创建的file包手动将当前目录加入环境变量######
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
######正常测试我们的项目应该已存在于pythonpath中所以不需要这么写#####
import pytest

from file.file import File


# 如果mock掉的方法不需要逻辑判断，直接使用ret_val指定返回值即可
@pytest.mark.usefixtures("mock")
@pytest.mark.prop("file.file.File.load", ret_val=File("直接mock返回值"))
def test_load1():
    assert File.load().filename == "直接mock返回值"


# 无论被mock的方法是异步还是同步，无脑指定返回值
# 不过异步的方法测试需要pytest-asyncio这个包支持，指定一个asyncio的mark才可以
@pytest.mark.asyncio
@pytest.mark.usefixtures("mock")
@pytest.mark.prop("file.file.File.load_async", ret_val=File("异步方法也能mock"))
async def test_load2():
    assert (await File.load_async()).filename == "异步方法也能mock"


# 如果我们用来替代的mock方法有一定的逻辑，我们可以指定一个ret_factory，指向替代方法的包地址
@pytest.mark.asyncio
@pytest.mark.usefixtures("mock")
@pytest.mark.prop("file.file.File.load_async", ret_factory="factories.mock_load")
async def test_load3():
    assert (await File.load_async()).filename == "通过工厂mock"


# 这种就是有业务逻辑的替代方法，他可以通过filename不同返回不同的File对象
@pytest.mark.usefixtures("mock")
@pytest.mark.prop("file.file.File.load", ret_factory="factories.mock_load", filename="还能给工厂传参")
def test_load4():
    assert File.load().filename == "还能给工厂传参"


# 装饰器太长怎么办，取个别名来缩短导包参数
from pytest_apistellar import prop_alias

file = prop_alias("file.file.File", "factories")


@pytest.mark.usefixtures("mock")
@file("load", ret_factory="mock_load", filename="使用别名装饰器，把前缀连起来")
def test_load4():
    assert File.load().filename == "使用别名装饰器，把前缀连起来"


# module作用域的mock
pytestmark = [
        file("load", ret_factory="mock_load", filename="这是一个module作用域的mock")
    ]


@pytest.mark.usefixtures("mock")
def test_load5():
    assert File.load().filename == "这是一个module作用域的mock"


@pytest.mark.usefixtures("mock")
class TestLoad(object):
    # class作用域的mock
    pytestmark = [
        file("load", ret_factory="mock_load", filename="这是一个class作用域的mock")
    ]

    def test_load6(self):
        assert File.load().filename == "这是一个class作用域的mock"

    # funtion作用域的mock
    @file("load", ret_factory="mock_load", filename="这是一个function作用域的mock")
    def test_load7(self):
        assert File.load().filename == "这是一个function作用域的mock"


