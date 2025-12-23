import asyncio
from src.methods.http_async import AsyncHTTPParser
from src.bd import VacancyDB
from src.utils.print_table import print_vacancies_table
from src.bd.cache import Cache


async def main():
    cache = Cache(ttl=600)
    parser = AsyncHTTPParser("Python developer", limit=3, cache=cache)
    vacancies = await parser.search()

    db = VacancyDB()
    db.save_many(vacancies)

    all_vacancies = db.get_all()
    print_vacancies_table(all_vacancies)


if __name__ == "__main__":
    asyncio.run(main())
