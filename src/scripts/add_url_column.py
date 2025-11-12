"""
Скрипт для добавления колонки url в таблицы properties и land_opportunities
"""

import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from data.database import engine, get_session


def add_url_columns():
    """
    Добавляет колонку url в таблицы properties и land_opportunities
    """
    session = get_session()

    try:
        print("Adding url column to properties table...")

        # Пробуем добавить колонку (если уже существует, получим ошибку)
        try:
            alter_query = text("""
                ALTER TABLE properties
                ADD COLUMN url VARCHAR(500)
            """)
            session.execute(alter_query)
            session.commit()
            print("SUCCESS: Column url added to properties table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column url already exists in properties table")
            else:
                raise

        print("\nAdding url column to land_opportunities table...")

        # Пробуем добавить колонку (если уже существует, получим ошибку)
        try:
            alter_query = text("""
                ALTER TABLE land_opportunities
                ADD COLUMN url VARCHAR(500)
            """)
            session.execute(alter_query)
            session.commit()
            print("SUCCESS: Column url added to land_opportunities table")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column url already exists in land_opportunities table")
            else:
                raise

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"ERROR adding columns: {e}")
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    add_url_columns()
