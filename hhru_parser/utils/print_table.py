from hhru_parser.methods.base import Vacancy


def print_vacancies_table(vacancies: list[Vacancy]):
    headers = (
        "TITLE", "COMPANY", "SALARY", "EXP",
        "EMPLOY", "RESP", "URL"
    )

    print(" | ".join(headers))
    print("-" * 120)

    for v in vacancies:
        print(
            f"{v.title[:25]:25} | "
            f"{v.company[:20]:20} | "
            f"{str(v.salary):10} | "
            f"{str(v.experience):8} | "
            f"{str(v.employment):10} | "
            f"{str(v.responses):5} | "
            f"{v.url[:40]}"
        )