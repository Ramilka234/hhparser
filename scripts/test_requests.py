import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from hhru_parser.methods import HTTP_Parser, API_Parser, Selenium_Parser, AsyncHTTPParser
from hhru_parser.bd.bd_vacancy import VacancyDB
from hhru_parser.stats.compute_by_vacancy import compute_stats

async def run_async_parser(query: str, limit: int):
    parser = AsyncHTTPParser(query, limit)
    return await parser.search()

def main():
    parser = argparse.ArgumentParser(description="Тестирование парсеров HH.ru")
    parser.add_argument("--test_query", type=str, required=True, help="Поисковый запрос (например 'ML Engineer')")
    parser.add_argument("-n", "--number", type=int, default=10, help="Количество вакансий для парсинга")
    parser.add_argument("--parser", type=str, choices=["http", "async", "api", "selenium"], default="async", help="Тип парсера")
    
    args = parser.parse_args()
    print(f"Поиск '{args.test_query}' с лимитом {args.number} используя '{args.parser}' парсер...")

    import time
    start_time = time.time()

    vacancies = []

    if args.parser == "async":
        vacancies = asyncio.run(run_async_parser(args.test_query, args.number))
    elif args.parser == "http":
        parser_instance = HTTP_Parser(args.test_query, args.number)
        vacancies = parser_instance.search()
    else:
        print(f"Парсер '{args.parser}' еще не реализован.")
        return

    end_time = time.time()
    elapsed = end_time - start_time
    
    
    if vacancies:
        # Save to DB
        db = VacancyDB()
        print("Сохранение в БД...")
        db.save_many(vacancies)
        print("Сохранено в БД.")

        # Save to CSV
        import csv
        csv_file = "vacancies.csv"
        # Append mode? No, usually overwrite last search result or maybe user wants accumulation?
        # User requested "export to csv", usually implies current result.
        # But for stats, they want global.
        # Let's keep CSV as "current search results" to avoid massive duplication or huge files.
        print(f"Сохранение в {csv_file}...")
        with open(csv_file, mode="w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["Название", "Компания", "Зарплата", "Опыт", "Занятость", "Отклики", "Ссылка", "Описание (кратко)"])
            for v in vacancies:
                desc_short = (v.description[:100] + "...") if v.description else ""
                writer.writerow([
                    v.title,
                    v.company,
                    v.salary,
                    v.experience,
                    v.employment,
                    v.responses,
                    v.url,
                    desc_short
                ])
        print(f"Сохранено в {csv_file}.")

    else:
        print("Вакансии не найдены.")

    # Compute stats on ALL data (Always run)
    try:
        db = VacancyDB()
        print("\nЗагрузка всех вакансий из БД для статистики...")
        all_vacancies = db.get_all()
        if all_vacancies:
            stats = compute_stats(all_vacancies)
            print("Сводка статистики (по всей БД):", stats)
        else:
            print("БД пуста, статистика не может быть вычислена.")
    except Exception as e:
        print(f"Ошибка при обновлении статистики: {e}")

    print("\n" + "="*40)
    print(f"⏱️  ВРЕМЯ ВЫПОЛНЕНИЯ: {elapsed:.2f} секунд")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
