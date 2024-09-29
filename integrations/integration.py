from abc import ABC, abstractmethod
class Integration(ABC):
    @abstractmethod
    def execute(self, new_passwd: str):
        pass
