import sys
from pathlib import Path
import sqlite3

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def main():
    print("Очистка базы данных...")
    db_path = Path("vacancies.db")
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM vacancies")
            conn.commit()
            conn.close()
            print("База данных очищена.")
        except Exception as e:
            print(f"Ошибка очистки базы данных: {e}")
    else:
        print("База данных не существует.")

if __name__ == "__main__":
    main()
