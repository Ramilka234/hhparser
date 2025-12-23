import sqlite3
from pathlib import Path
from hhru_parser.methods.base import Vacancy
from typing import Iterable

class VacancyDB:
    def __init__(self, db_path: str | Path = "vacancies.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            salary TEXT,
            experience TEXT,
            employment TEXT,
            responses TEXT,
            description TEXT,
            url TEXT UNIQUE
        )
        """)
        self.conn.commit()

    def save(self, vacancy: Vacancy):
        self.conn.execute("""
        INSERT OR IGNORE INTO vacancies
        (title, company, salary, experience, employment, responses, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy.title,
            vacancy.company,
            vacancy.salary,
            vacancy.experience,
            vacancy.employment,
            vacancy.responses,
            vacancy.description,
            vacancy.url,
        ))
        self.conn.commit()

    def save_many(self, vacancies: Iterable[Vacancy]):
        self.conn.executemany("""
        INSERT OR IGNORE INTO vacancies
        (title, company, salary, experience, employment, responses, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                v.title,
                v.company,
                v.salary,
                v.experience,
                v.employment,
                v.responses,
                v.description,
                v.url,
            )
            for v in vacancies
        ])
        self.conn.commit()

    def get_all(self) -> list[Vacancy]:
        cursor = self.conn.execute("SELECT title, company, salary, experience, employment, responses, description, url FROM vacancies")
        rows = cursor.fetchall()

        return [
            Vacancy(*row)
            for row in rows
        ]
    
    