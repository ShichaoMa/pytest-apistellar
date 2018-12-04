import pytest
from pytest_apistellar.utils import load


class TestLoad(object):

    def test_load_nomal(self):
        assert load("os.path").__name__ == "posixpath"

    def test_load_not_found_attr(self):
        with pytest.raises(AttributeError):
            load("os.path.a")

    def test_load_not_found_module(self):
        with pytest.raises(ImportError):
            load("fdsff")