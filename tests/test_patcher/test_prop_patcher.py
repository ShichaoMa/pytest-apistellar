import pytest


@pytest.fixture(scope="session", params=[x for x in range(1, 5)])
def a(request):
    return request.param


pytestmark = [
    pytest.mark.prop("factories.TestClass.get_data_module",
                     ret_factory=lambda a, **kwargs: a * 3, fixture_inject=True)
]


@pytest.mark.prop("factories.TestClass.get_data_class",
                     ret_factory=lambda a, **kwargs: a * 4, fixture_inject=True)
class TestPropPatcher(object):

    @pytest.mark.prop("factories.TestClass.get_data_function",
                     ret_factory=lambda a, **kwargs: a * 5, fixture_inject=True)
    def test_factory(self, a):
        from factories import TestClass
        assert TestClass.get_data_function() == a * 5
        assert TestClass.get_data_class() == 4
        assert TestClass.get_data_module() == 3
