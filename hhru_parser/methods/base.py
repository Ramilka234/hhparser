from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Vacancy:
    """
    Унифицированная модель вакансии
    """
    title: str
    company: str
    salary: str | None
    experience: str | None
    employment: str | None
    responses: int | None
    description: str
    url: str


class BaseParser(ABC):
    """
    Базовый класс для всех парсеров HH
    """

    def __init__(self, query: str, limit: int = 5):
        self.query = query
        self.limit = limit

    @abstractmethod
    def search(self) -> Iterable[Vacancy]:
        """
        Должен вернуть список вакансий
        """
        raise NotImplementedError