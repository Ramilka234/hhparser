import asyncio
import random
import time
from typing import List, Optional
import aiohttp
from bs4 import BeautifulSoup
from aiohttp import ClientResponseError, ClientError
from tqdm import tqdm

from hhru_parser.methods import BaseParser, Vacancy

class AsyncHTTPParser(BaseParser):
    BASE_URL = "https://hh.ru/search/vacancy"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    def __init__(self, query: str, limit: int = 10, page: int = 0, cookies: Optional[dict] = None):
        super().__init__(query, limit, page, cookies)
        self.current_delay = 1.0  # Initial delay in seconds

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> str:
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
                return tag.get_text(separator=" ", strip=True) if tag else None

            # Experience fallback
            exp = get_text('[data-qa="vacancy-experience"]') or get_text('[data-qa="work-experience-text"]')
            
            emp_parts = []
            for qa in ["vacancy-view-employment-mode", "work-formats-text", "working-hours-text", "work-schedule-by-days-text", "common-employment-text"]:
                txt = get_text(f'[data-qa="{qa}"]')
                if txt: emp_parts.append(txt)
            employment = ", ".join(emp_parts) if emp_parts else None

            responses = get_text('[data-qa="vacancy-view-responses-count"]') or get_text('[data-qa="vacancyResponses-button-text"]')
            viewers = get_text('[data-qa="vacancy-view-viewers-count"]')

            skills_section = soup.select_one('[data-qa="skills-element"]')
            if skills_section:
                skills = ", ".join([s.get_text(strip=True) for s in skills_section.select('[data-qa="bloko-tag__text"], .magritte-tag__label___YHV-o_5-0-7, .magritte-tag__label, [class*="magritte-tag__label"]')])
            else:
                skills = None

            date_tag = soup.select_one('[data-qa="vacancy-view-publication-date"]')
            if not date_tag:
                date_elem = soup.find(string=lambda x: x and 'опубликована' in x.lower())
                if date_elem and date_elem.parent.name not in ['script', 'style', 'title', 'head', 'meta', 'link']:
                    date_tag = date_elem.parent
            
            def clean_field(text):
                if not text: return None
                text = text.strip()
                if text.startswith('{') or text.startswith('[') or len(text) > 1000:
                    return None
                return text

            published_at = clean_field(date_tag.get_text(separator=" ", strip=True)) if date_tag else None

            return {
                "description": get_text('[data-qa="vacancy-description"]'),
                "salary": get_text('[data-qa="vacancy-salary"]'),
                "experience": clean_field(exp),
                "employment": clean_field(employment),
                "responses": clean_field(responses),
                "viewers": clean_field(viewers),
                "skills": clean_field(skills),
                "published_at": published_at,
            }
        except Exception as e:
            print(f"⚠️ Ошибка парсинга страницы {url}: {e}")
            return {
                "description": None, "salary": None, "experience": None, 
                "employment": None, "responses": None, "viewers": None,
                "skills": None, "published_at": None
            }

    async def search(self) -> List[Vacancy]:
        vacancies = []
        current_page = self.page
        items_per_page = 50 

        with tqdm(total=self.limit, desc=f"HH Search: {self.query}") as pbar:
            async with aiohttp.ClientSession(cookies=self.cookies) as session:
                while len(vacancies) < self.limit:
                    params = {
                        "text": self.query,
                        "area": 1, 
                        "items_on_page": items_per_page,
                        "search_field": "name",
                        "page": current_page,
                    }

                    url = self.BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
                    try:
                        html = await self._fetch(session, url)
                    except Exception as e:
                        tqdm.write(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить страницу поиска {current_page}: {e}")
                        break

                    soup = BeautifulSoup(html, "html.parser")
                    items = soup.select('[data-qa="vacancy-serp__vacancy"]')
                    
                    if not items:
                        if current_page == self.page:
                            print("⚠️ Вакансии не найдены или изменилась верстка.")
                        break

                    current_page_vacancies = []
                    tasks = []

                    for item in items:
                        if len(vacancies) + len(current_page_vacancies) >= self.limit:
                            break

                        title_tag = item.select_one('[data-qa="serp-item__title"]') or item.select_one("a.bloko-link")
                        company_tag = item.select_one('[data-qa="vacancy-serp__vacancy-employer"]')
                        
                        if not title_tag:
                            continue

                        vacancy_url = title_tag["href"]
                        if not vacancy_url.startswith("http"):
                            vacancy_url = "https://hh.ru" + vacancy_url

                        try:
                            v = Vacancy(
                                title=title_tag.text.strip(),
                                company=company_tag.text.strip() if company_tag else "Unknown",
                                salary=None,
                                experience=None,
                                employment=None,
                                responses=None,
                                viewers=None,
                                skills=None,
                                published_at=None,
                                description="",
                                url=vacancy_url,
                            )
                            current_page_vacancies.append(v)
                            tasks.append(self._parse_vacancy_page(session, vacancy_url))
                        except Exception as e:
                            print(f"Пропуск вакансии из-за ошибки: {e}")

                    if tasks:
                        details_list = await asyncio.gather(*tasks)
                        for v, details in zip(current_page_vacancies, details_list):
                            v.salary = details.get("salary")
                            v.experience = details.get("experience")
                            v.employment = details.get("employment")
                            v.responses = details.get("responses")
                            v.viewers = details.get("viewers")
                            v.skills = details.get("skills")
                            v.published_at = details.get("published_at")
                            v.description = details.get("description", "")
                    
                    vacancies.extend(current_page_vacancies)
                    pbar.update(len(current_page_vacancies))
                    current_page += 1

                    if current_page > self.page + 40: 
                        break

            return vacancies
