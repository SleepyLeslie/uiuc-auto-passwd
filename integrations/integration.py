import configparser
from typing import Union
from abc import ABC, abstractmethod

class Integration(ABC):

    @abstractmethod
    def __init__(self, config: Union[None, configparser.SectionProxy] = None):
        pass

    @abstractmethod
    def execute(self, new_passwd: str) -> int:
        pass
