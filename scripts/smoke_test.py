import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from hhru_parser.methods.http_async import AsyncHTTPParser
from hhru_parser.bd import VacancyDB
# from src.utils.print_table import print_vacancies_table

async def main():
    parser = AsyncHTTPParser("Python developer", limit=3)
    vacancies = await parser.search()

    db = VacancyDB()
    db.save_many(vacancies)

    all_vacancies = db.get_all()
    print_vacancies_table(all_vacancies)


if __name__ == "__main__":
    asyncio.run(main())
