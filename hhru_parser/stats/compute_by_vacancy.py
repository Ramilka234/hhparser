import re
import matplotlib.pyplot as plt
from collections import Counter, defaultdict
from typing import List
from hhru_parser.methods.base import Vacancy

def parse_salary(salary_str: str | None) -> float | None:
    if not salary_str:
        return None
    
    # Currency Rates (Approximate)
    rates = {
        'usd': 90.0,
        'eur': 100.0,
        'kzt': 0.2,
        'byn': 28.0,
        'kgs': 1.0, # Kyrgyz som approx 1 rub
        'uzs': 0.007,
    }
    
    lower_str = salary_str.lower().replace('\xa0', '').replace(' ', '')
    
    # Detect currency
    rate = 1.0
    for cur, r in rates.items():
        if cur in lower_str or ('$' in lower_str and cur == 'usd') or ('€' in lower_str and cur == 'eur'):
            rate = r
            break
            
    # Remove currency symbols and text to leave numbers
    # We remove typically year-like patterns if they are not part of salary range?
    # Actually simple extraction is best, years usually in experience field.
    
    nums = re.findall(r'\d+', lower_str)
    if not nums:
        return None
    
    # Calculate average
    nums = [float(n) for n in nums]
    
    # Filter out year-like numbers if they are small and likely not salary?
    # Use simple heuristic: Salary > 1000 RUB usually
    # But checking raw numbers might misinterpret "1 2 года" mixed in?
    # Salary field usually only contains salary info.
    
    avg_val = sum(nums) / len(nums)
    converted = avg_val * rate
    
    return converted if converted > 5000 else None # Filter out errors/hourly parts

def compute_stats(vacancies: List[Vacancy], output_prefix: str = "stats"):
    print(f"Вычисление статистики для {len(vacancies)} вакансий...")
    
    companies = Counter()
    salaries = []
    experiences = Counter()
    
    for v in vacancies:
        if v.company:
            companies[v.company] += 1
        
        avg_salary = parse_salary(v.salary)
        if avg_salary:
            salaries.append(avg_salary)
            
        experiences[v.experience or "Не указано"] += 1

    # 1. Top Companies Plot
    top_companies = companies.most_common(10)
    if top_companies:
        plt.figure(figsize=(10, 6))
        names, counts = zip(*top_companies)
        plt.barh(names, counts)
        plt.title("Топ 10 Компаний")
        plt.xlabel("Количество")
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_companies.png")
        print(f"Сохранено {output_prefix}_companies.png")
        plt.close()

    # 2. Salary Distribution
    if salaries:
        plt.figure(figsize=(10, 6))
        plt.hist(salaries, bins=20, edgecolor='black')
        plt.title("Распределение зарплат (Среднее)")
        plt.xlabel("Зарплата (Руб/Валюта)")
        plt.ylabel("Количество")
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_salaries.png")
        print(f"Сохранено {output_prefix}_salaries.png")
        plt.close()

    # 3. Experience Pie Chart
    if experiences:
        plt.figure(figsize=(8, 8))
        plt.pie(experiences.values(), labels=experiences.keys(), autopct='%1.1f%%')
        plt.title("Требования к опыту")
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_experience.png")
        print(f"Сохранено {output_prefix}_experience.png")
        plt.close()

    return {
        "total": len(vacancies),
        "companies_count": len(companies),
        "avg_salary": sum(salaries) / len(salaries) if salaries else 0
    }
