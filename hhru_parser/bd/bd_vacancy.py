import sqlite3
from pathlib import Path
from hhru_parser.methods.base import Vacancy
from typing import Iterable

class VacancyDB:
    def __init__(self, db_path: str | Path = "vacancies.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path, timeout=20)
        self.conn.execute("PRAGMA journal_mode=WAL")
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
            viewers TEXT,
            skills TEXT,
            published_at TEXT,
            description TEXT,
            url TEXT UNIQUE
        )
        """)
        cursor = self.conn.execute("PRAGMA table_info(vacancies)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'viewers' not in columns:
            self.conn.execute("ALTER TABLE vacancies ADD COLUMN viewers TEXT")
        if 'skills' not in columns:
            self.conn.execute("ALTER TABLE vacancies ADD COLUMN skills TEXT")
        if 'published_at' not in columns:
            self.conn.execute("ALTER TABLE vacancies ADD COLUMN published_at TEXT")
        self.conn.commit()

    def save(self, vacancy: Vacancy):
        self.conn.execute("""
        INSERT OR IGNORE INTO vacancies
        (title, company, salary, experience, employment, responses, viewers, skills, published_at, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vacancy.title,
            vacancy.company,
            vacancy.salary,
            vacancy.experience,
            vacancy.employment,
            vacancy.responses,
            vacancy.viewers,
            vacancy.skills,
            vacancy.published_at,
            vacancy.description,
            vacancy.url,
        ))
        self.conn.commit()

    def save_many(self, vacancies: Iterable[Vacancy]) -> int:
        count_before = self.conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
        self.conn.executemany("""
        INSERT OR IGNORE INTO vacancies
        (title, company, salary, experience, employment, responses, viewers, skills, published_at, description, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                v.title,
                v.company,
                v.salary,
                v.experience,
                v.employment,
                v.responses,
                v.viewers,
                v.skills,
                v.published_at,
                v.description,
                v.url,
            )
            for v in vacancies
        ])
        self.conn.commit()
        count_after = self.conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
        return count_after - count_before

    def get_all(self) -> list[Vacancy]:
        cursor = self.conn.execute("SELECT title, company, salary, experience, employment, responses, viewers, skills, published_at, description, url FROM vacancies")
        rows = cursor.fetchall()

        return [
            Vacancy(*row)
            for row in rows
        ]

    def close(self):
        self.conn.close()

    
    