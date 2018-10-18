import pytest

from os import getcwd
from os.path import dirname

pytestmark = [pytest.mark.path(dirname(dirname((dirname(__file__)))))]


@pytest.mark.usefixtures("mock")
def test_root_path():
    assert getcwd() == dirname(dirname(dirname(__file__)))


@pytest.mark.usefixtures("mock")
class TestPathPatcher(object):
    pytestmark = [pytest.mark.path(dirname(dirname(__file__)))]

    def test_current_class_path(self):
        assert getcwd() == dirname(dirname(__file__))

    @pytest.mark.path(dirname(__file__))
    def test_current_path(self):
        assert getcwd() == dirname(__file__)

