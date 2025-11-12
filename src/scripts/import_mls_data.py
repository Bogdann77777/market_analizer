"""
CLI скрипт для импорта MLS CSV файлов в базу данных
Использование: python import_mls_data.py <путь_к_csv_файлу>
"""

import sys
import os
import argparse

# Установить UTF-8 кодировку для вывода в консоль
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import create_tables
from data.mls_importer import import_csv_file


def main():
    """
    Главная функция CLI скрипта импорта MLS данных
    """
    # Настроить парсер аргументов
    parser = argparse.ArgumentParser(
        description='Импорт MLS CSV файла в базу данных Asheville Land Analyzer'
    )
    parser.add_argument(
        'csv_file',
        type=str,
        help='Путь к CSV файлу с MLS данными'
    )
    parser.add_argument(
        '--create-tables',
        action='store_true',
        help='Создать таблицы БД перед импортом (если не существуют)'
    )

    # Парсить аргументы
    args = parser.parse_args()

    csv_file_path = args.csv_file

    # Проверить существование файла
    if not os.path.exists(csv_file_path):
        print(f"❌ Ошибка: Файл не найден: {csv_file_path}")
        sys.exit(1)

    print("=" * 60)
    print("     ASHEVILLE LAND ANALYZER - MLS DATA IMPORT")
    print("=" * 60)
    print()

    # Создать таблицы если указан флаг
    if args.create_tables:
        print("🔧 Создаю таблицы базы данных...")
        create_tables()
        print("✅ Таблицы созданы\n")

    # Запустить импорт
    try:
        new_count = import_csv_file(csv_file_path)

        print("\n" + "=" * 60)
        if new_count > 0:
            print(f"✅ ИМПОРТ ЗАВЕРШЕН УСПЕШНО!")
            print(f"   Добавлено новых домов: {new_count}")
        else:
            print("⚠️  ИМПОРТ ЗАВЕРШЕН")
            print("   Новых домов не добавлено (возможно все уже в базе)")
        print("=" * 60)

        sys.exit(0)

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ОШИБКА ИМПОРТА: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
