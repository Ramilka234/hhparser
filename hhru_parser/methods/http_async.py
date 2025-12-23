import asyncio
import random
import time
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup
from aiohttp import ClientResponseError, ClientError

from hhru_parser.methods import BaseParser, Vacancy
from hhru_parser.bd.cache import Cache

class AsyncHTTPParser(BaseParser):
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
        self.current_delay = 1.0  # Initial delay in seconds

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> str:
        cached = self.cache.get(url)
        if cached:
            return cached

        retries = 5
        delay = self.current_delay

        for attempt in range(retries):
            try:
                # Add random jitter to avoid synchronized bursts
                await asyncio.sleep(delay + random.uniform(0, 0.5))
                
                async with session.get(url, headers=self.HEADERS, timeout=10) as resp:
                    if resp.status in (403, 429):
                        # Banned or Rate Limited
                        print(f"⚠️ Получен статус {resp.status} для {url}. Ожидание {delay:.2f}с...")
                        delay *= 2.0  # Exponential backoff
                        self.current_delay = max(self.current_delay, delay) # Update global delay
                        continue
                    
                    resp.raise_for_status()
                    text = await resp.text()
                    
                    # Success: linearly decrease delay if it's high
                    if self.current_delay > 1.0:
                         self.current_delay = max(1.0, self.current_delay - 0.5)

                    self.cache.set(url, text)
                    return text

            except (ClientError, asyncio.TimeoutError) as e:
                print(f"❌ Сетевая ошибка для {url}: {e}. Повтор через {delay}с...")
                delay *= 2
                await asyncio.sleep(delay)
        
        raise Exception(f"Не удалось получить {url} после {retries} попыток")

    async def _parse_vacancy_page(self, session: aiohttp.ClientSession, url: str) -> dict:
        try:
            html = await self._fetch(session, url)
            soup = BeautifulSoup(html, "html.parser")

            def get_text(selector):
                tag = soup.select_one(selector)
                return tag.text.strip() if tag else None

            return {
                "description": get_text('[data-qa="vacancy-description"]'),
                "salary": get_text('[data-qa="vacancy-salary"]'),
                "experience": get_text('[data-qa="vacancy-experience"]'),
                # Employment: try new common selector, then old one
                "employment": get_text('[data-qa="common-employment-text"]') or get_text('[data-qa="vacancy-view-employment-mode"]'),
                # Responses: try responses count, then viewers count
                "responses": get_text('[data-qa="vacancy-view-responses-count"]') or get_text('[data-qa="vacancy-viewers-count"]'),
            }
        except Exception as e:
            print(f"⚠️ Ошибка парсинга страницы {url}: {e}")
            return {
                "description": None, "salary": None, "experience": None, 
                "employment": None, "responses": None
            }

    async def search(self) -> List[Vacancy]:
        params = {
            "text": self.query,
            "area": 1,  # Moscow
            "items_on_page": self.limit,
            "search_field": "name", # Search in title
        }

        async with aiohttp.ClientSession() as session:
            url = self.BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
            try:
                html = await self._fetch(session, url)
            except Exception as e:
                print(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить страницу поиска: {e}")
                return []

            soup = BeautifulSoup(html, "html.parser")
            items = soup.select('[data-qa="vacancy-serp__vacancy"]')
            
            if not items:
                print("⚠️ Вакансии не найдены или изменилась верстка.")
                return []

            vacancies = []
            tasks = []

            for item in items[:self.limit]:
                # Using standard selectors based on common HH structure
                title_tag = item.select_one('[data-qa="serp-item__title"]') or item.select_one("a.bloko-link")
                company_tag = item.select_one('[data-qa="vacancy-serp__vacancy-employer"]')
                
                if not title_tag:
                    continue

                vacancy_url = title_tag["href"]
                # Handle relative URLs if any (though usually absolute)
                if not vacancy_url.startswith("http"):
                    vacancy_url = "https://hh.ru" + vacancy_url

                try:
                    vacancies.append(
                        Vacancy(
                            title=title_tag.text.strip(),
                            company=company_tag.text.strip() if company_tag else "Unknown",
                            salary=None, # Filled later
                            experience=None, # Filled later
                            employment=None, # Filled later
                            responses=None, # Filled later
                            description="", # Filled later
                            url=vacancy_url,
                        )
                    )
                    tasks.append(self._parse_vacancy_page(session, vacancy_url))
                except Exception as e:
                    print(f"Пропуск вакансии из-за ошибки: {e}")

            # Fetch details in parallel
            if tasks:
                details_list = await asyncio.gather(*tasks)
                
                for vacancy, details in zip(vacancies, details_list):
                    vacancy.salary = details.get("salary")
                    vacancy.experience = details.get("experience")
                    vacancy.employment = details.get("employment")
                    vacancy.responses = details.get("responses")
                    vacancy.description = details.get("description", "")

            return vacancies
