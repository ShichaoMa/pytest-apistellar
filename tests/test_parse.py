import pytest


class TestParse(object):

    @pytest.mark.prop("os.b.c.d", ret_val=1)
    def test_cascade_mock(self):
        import os
        assert hasattr(os, "b")
        assert hasattr(os.b, "c")
        assert os.b.c.d == 1
