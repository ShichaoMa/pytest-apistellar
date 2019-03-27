# -*- coding:utf-8 -*-
data = dict(a=5, b=8)


mock_get_data_session = lambda a, **kwargs: a*2


class TestClass(object):

    @classmethod
    def get_data_session(cls):
        return a

    @classmethod
    def get_data_module(cls):
        return a

    @classmethod
    def get_data_class(cls):
        return a

    @classmethod
    def get_data_function(cls):
        return a