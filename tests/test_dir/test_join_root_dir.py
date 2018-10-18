import os
import pytest


@pytest.mark.path(os.path.dirname(os.path.dirname(__file__)))
def test_join_root_dir(join_root_dir):
    assert os.path.join(os.getcwd(), ".") == join_root_dir(".")
