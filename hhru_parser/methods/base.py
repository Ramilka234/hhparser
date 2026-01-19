from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass
class Vacancy:
    """
    Унифицированная модель вакансии
    """
    title: str
    company: str
    salary: Optional[str]
    experience: Optional[str]
    employment: Optional[str]
    responses: Optional[str]
    viewers: Optional[str]
    skills: Optional[str]
    published_at: Optional[str]
    description: str
    url: str


class BaseParser(ABC):
    """
    Базовый класс для всех парсеров HH
    """

    def __init__(self, query: str, limit: int = 5, page: int = 0, cookies: Optional[dict] = None):
        self.query = query
        self.limit = limit
        self.page = page
        self.cookies = cookies or {}

    @abstractmethod
    def search(self) -> Iterable[Vacancy]:
        """
        Должен вернуть список вакансий
        """
        raise NotImplementedError