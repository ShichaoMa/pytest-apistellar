import pytest


class DataProxy(object):
    """
    由于pytest是先导出当前测试文件，再解析配置文件，
    所以如果不使用这个代码懒加载一下factories中的data,
    就会导致ini没有加载就发生了import，即而syspath也没有生效
    """
    @property
    def data(self):
        from factories import data
        return data

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, item):
        return self.data[item]

    def __getattr__(self, item):
        return getattr(self.data, item)


pytestmark = [pytest.mark.item(DataProxy(), a=2, b=1)]


class TestItemPatcher(object):

    pytestmark = [pytest.mark.item(DataProxy(), a=3, b=4)]

    @pytest.mark.item(DataProxy(), a=8, b=9)
    def test_function_scope_mock(self):
        assert DataProxy()["a"] == 8
        assert DataProxy()["b"] == 9

    def test_class_scope_mock(self):
        assert DataProxy()["a"] == 3
        assert DataProxy()["b"] == 4


def test_module_scope_mock():
    assert DataProxy()["a"] == 2
    assert DataProxy()["b"] == 1
