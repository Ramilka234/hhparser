import time
import requests
import time
import random
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from hhru_parser.methods import BaseParser, Vacancy
from hhru_parser.bd.cache import Cache

class HTTP_Parser(BaseParser):
    BASE_URL = "https://hh.ru/search/vacancy"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    def __init__(self, query: str, limit: int = 10, cache: Cache | None = None):
        super().__init__(query, limit)
        self.cache = cache or Cache(ttl=300)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.current_delay = 1.0

    def _fetch(self, url: str) -> str:
        cached = self.cache.get(url)
        if cached:
            return cached

        retries = 3
        delay = self.current_delay

        for attempt in range(retries):
            try:
                time.sleep(delay + random.uniform(0, 0.5))
                resp = self.session.get(url, timeout=10)
                
                if resp.status_code in (403, 429):
                    print(f"⚠️ Синх: Получен статус {resp.status_code} для {url}. Ожидание...")
                    delay *= 2.0
                    self.current_delay = max(self.current_delay, delay)
                    continue

                resp.raise_for_status()
                
                if self.current_delay > 1.0:
                    self.current_delay = max(1.0, self.current_delay - 0.5)

                text = resp.text
                self.cache.set(url, text)
                return text
            except RequestException as e:
                print(f"❌ Синх ошибка: {e}")
                delay *= 2
                time.sleep(delay)

        raise Exception(f"Не удалось получить {url}")

    def _get_text(self, soup, selector):
        tag = soup.select_one(selector)
        return tag.text.strip() if tag else None

    def _parse_vacancy_page(self, url: str) -> dict:
        try:
            html = self._fetch(url)
            soup = BeautifulSoup(html, "html.parser")

            return {
                "description": self._get_text(soup, '[data-qa="vacancy-description"]'),
                "salary": self._get_text(soup, '[data-qa="vacancy-salary"]'),
                "experience": self._get_text(soup, '[data-qa="vacancy-experience"]'),
                # Employment: try new common selector, then old one
                "employment": self._get_text(soup, '[data-qa="common-employment-text"]') or self._get_text(soup, '[data-qa="vacancy-view-employment-mode"]'),
                # Responses: try responses count, then viewers count
                "responses": self._get_text(soup, '[data-qa="vacancy-view-responses-count"]') or self._get_text(soup, '[data-qa="vacancy-viewers-count"]'),
            }
        except Exception:
            return {}

    def search(self) -> List[Vacancy]:
        params = {
            "text": self.query,
            "area": 1,
            "items_on_page": self.limit,
            "search_field": "name", 
        }

        response = requests.get(
            self.BASE_URL,
            params=params,
            headers=self.HEADERS,
            timeout=15,
        )

        print("STATUS:", response.status_code)
        print("URL:", response.url)

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        vacancies = []

        items = soup.select('[data-qa="vacancy-serp__vacancy"]')

        if not items:
            print("⚠️ Вакансии не найдены — HH мог изменить верстку")

        for item in items[: self.limit]:
            title_tag = item.select_one('[data-qa="serp-item__title"]')
            company_tag = item.select_one('[data-qa="vacancy-serp__vacancy-employer"]')
            salary_tag = item.select_one('[data-qa="vacancy-serp__vacancy-compensation"]')

            if not title_tag:
                continue

            vacancies.append(
                Vacancy(
                    title=title_tag.text.strip(),
                    company=company_tag.text.strip() if company_tag else "",
                    salary=salary_tag.text.strip() if salary_tag else None,
                    experience=None,
                    employment=None,
                    responses=None,
                    description="",
                    url=title_tag["href"],
                )
            )

            time.sleep(1)  # антибан

        return vacancies
