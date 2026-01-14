from abc import ABC, abstractmethod

class BaseTranslator(ABC):
    def __init__(self, source_lang="auto", target_lang="zh"):
        self.source_lang = source_lang
        self.target_lang = target_lang

    @abstractmethod
    def translate(self, text):
        pass
