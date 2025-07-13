from abc import ABC, abstractmethod


class Check(ABC):
    name = None  # имя проверки

    def __init__(self, config):
        self.config = config

    @abstractmethod
    async def run(self):
        pass
