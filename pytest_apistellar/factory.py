"""
数据(对象生产工厂)
"""
from abc import ABC, abstractmethod


class Factory(ABC):

    @abstractmethod
    def product(self):
        """
        子类实现的生产函数，返回生产好的数据或对象
        :return:
        """