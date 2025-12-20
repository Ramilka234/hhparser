import time
import requests
from bs4 import BeautifulSoup

from src.methods.base import BaseParser, Vacancy


class HTTP_Parser(BaseParser):

    BASE_URL = "https://hh.ru/search/vacancy"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    def search(self):
        params = {
            "text": self.query,
            "area": 1,
            "items_on_page": self.limit,
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
            print("⚠️ No vacancies found — HH may have changed layout")

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
