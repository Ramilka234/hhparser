import time
import random
import requests
from typing import List, Optional
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
from tqdm import tqdm

from hhru_parser.methods import BaseParser, Vacancy

class HTTP_Parser(BaseParser):
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
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        if self.cookies:
            self.session.cookies.update(self.cookies)
        self.current_delay = 1.0

    def _fetch(self, url: str) -> str:
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

            def get_text(selector):
                tag = soup.select_one(selector)
                return tag.get_text(separator=" ", strip=True) if tag else None

            exp = get_text('[data-qa="vacancy-experience"]') or get_text('[data-qa="work-experience-text"]')
            
            emp_parts = []
            for qa in ["vacancy-view-employment-mode", "work-formats-text", "working-hours-text", "work-schedule-by-days-text"]:
                txt = get_text(f'[data-qa="{qa}"]')
                if txt: emp_parts.append(txt)
            employment = ", ".join(emp_parts) if emp_parts else None

            responses = get_text('[data-qa="vacancy-view-responses-count"]') or get_text('[data-qa="vacancyResponses-button-text"]')
            viewers = get_text('[data-qa="vacancy-view-viewers-count"]')

            skills_section = soup.select_one('[data-qa="skills-element"]')
            if skills_section:
                skills = ", ".join([s.get_text(strip=True) for s in skills_section.select('[data-qa="bloko-tag__text"], [class*="magritte-tag__label"]')])
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
        except Exception:
            return {}

    def search(self) -> List[Vacancy]:
        vacancies = []
        current_page = self.page
        items_per_page = 50

        with tqdm(total=self.limit, desc=f"HH Search (Sync): {self.query}") as pbar:
            while len(vacancies) < self.limit:
                params = {
                    "text": self.query,
                    "area": 1,
                    "items_on_page": items_per_page,
                    "search_field": "name",
                    "page": current_page,
                }

                try:
                    response = self.session.get(
                        self.BASE_URL,
                        params=params,
                        timeout=15,
                    )
                    response.raise_for_status()
                except Exception as e:
                    # tqdm.write(f"Ошибка при получении страницы поиска {current_page}: {e}") # Removed conflict print
                    break

                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.select('[data-qa="vacancy-serp__vacancy"]')

                if not items:
                    # if current_page == self.page: # Removed conflict print
                    #     print("⚠️ Вакансии не найдены — HH мог изменить верстку") # Removed conflict print
                    break

                for item in items:
                    if len(vacancies) >= self.limit:
                        break
                        
                    title_tag = item.select_one('[data-qa="serp-item__title"]') or item.select_one("a.bloko-link")
                    company_tag = item.select_one('[data-qa="vacancy-serp__vacancy-employer"]')
                    
                    if not title_tag:
                        continue

                    vacancy_url = title_tag["href"]
                    if not vacancy_url.startswith("http"):
                        vacancy_url = "https://hh.ru" + vacancy_url

                    details = self._parse_vacancy_page(vacancy_url)

                    vacancies.append(
                        Vacancy(
                            title=title_tag.text.strip(),
                            company=company_tag.text.strip() if company_tag else "Unknown",
                            salary=details.get("salary"),
                            experience=details.get("experience"),
                            employment=details.get("employment"),
                            responses=details.get("responses"),
                            viewers=details.get("viewers"),
                            skills=details.get("skills"),
                            published_at=details.get("published_at"),
                            description=details.get("description", ""),
                            url=vacancy_url,
                        )
                    )
                    pbar.update(1)
                
                current_page += 1
                if current_page > self.page + 40:
                    break

        return vacancies
