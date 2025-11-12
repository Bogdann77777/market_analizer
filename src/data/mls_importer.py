"""
Модуль импорта данных из MLS CSV файлов
Обрабатывает CSV с домами, геокодирует, рассчитывает метрики
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Property, get_session
from data.geocoder import geocode_address, batch_geocode
from analyzers.price_calculator import (
    calculate_price_per_sqft,
    calculate_days_on_market,
    extract_street_name
)
from config import ARCHIVE_SOLD_AFTER_DAYS


def normalize_redfin_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Нормализует имена колонок из Redfin CSV в ожидаемый формат

    Args:
        df: DataFrame с данными Redfin

    Returns:
        DataFrame с нормализованными именами колонок
    """
    # Маппинг Redfin колонок на ожидаемые имена
    column_mapping = {
        'ADDRESS': 'Address',
        'CITY': 'City',
        'STATE OR PROVINCE': 'State',
        'ZIP OR POSTAL CODE': 'Zip',
        'PRICE': 'ListPrice',
        'BEDS': 'Bedrooms',
        'BATHS': 'Bathrooms',
        'SQUARE FEET': 'Sqft',
        'LOT SIZE': 'LotSize',
        'STATUS': 'Status',
        'MLS#': 'MLSNumber',
        'SOLD DATE': 'SaleDate',
        'DAYS ON MARKET': 'DaysOnMarket',
        'LATITUDE': 'Latitude',
        'LONGITUDE': 'Longitude'
    }

    # Переименовать колонки
    df_normalized = df.rename(columns=column_mapping)

    return df_normalized


def validate_csv_structure(df: pd.DataFrame) -> bool:
    """
    Валидирует структуру CSV файла

    Args:
        df: DataFrame с данными

    Returns:
        True если структура валидна
    """
    # Обязательные колонки
    required_columns = ['Address', 'Sqft', 'Status']

    # Проверить наличие обязательных колонок
    for col in required_columns:
        if col not in df.columns:
            print(f"❌ Отсутствует обязательная колонка: {col}")
            return False

    # Должна быть хотя бы одна колонка с ценой
    price_columns = ['SalePrice', 'ListPrice']
    has_price = any(col in df.columns for col in price_columns)

    if not has_price:
        print(f"❌ Отсутствуют колонки с ценой: {price_columns}")
        return False

    return True


def check_duplicate(mls_number: str) -> Optional[Property]:
    """
    Проверяет существование дома с таким MLS номером в БД

    Args:
        mls_number: MLS номер для проверки

    Returns:
        Property объект если найден, иначе None
    """
    session = get_session()
    try:
        existing = session.query(Property).filter_by(mls_number=mls_number).first()
        return existing
    finally:
        session.close()


def update_property_status(session, mls_number: str, new_data: Dict) -> Property:
    """
    Обновляет статус существующего дома если изменился

    Args:
        session: SQLAlchemy сессия
        mls_number: MLS номер дома
        new_data: Новые данные из CSV

    Returns:
        Обновленный Property объект
    """
    # Получить объект в текущей сессии
    existing = session.query(Property).filter_by(mls_number=mls_number).first()

    if not existing:
        return None

    updated = False

    # Обновить URL если есть
    if new_data.get('url') and not existing.url:
        existing.url = new_data['url']
        updated = True

    # Проверить изменился ли статус
    if existing.status != new_data.get('status'):
        existing.status = new_data['status']
        updated = True

        # Если изменился на sold - обновить sale_date и sale_price
        if new_data['status'] == 'sold':
            existing.sale_date = new_data.get('sale_date')
            existing.sale_price = new_data.get('sale_price')

            # Пересчитать price_per_sqft
            if existing.sale_price and existing.sqft:
                existing.price_per_sqft = calculate_price_per_sqft(
                    existing.sale_price, existing.sqft
                )

            # Пересчитать days_on_market
            if existing.list_date and existing.sale_date:
                existing.days_on_market = calculate_days_on_market(
                    existing.list_date, existing.sale_date
                )

    if updated:
        existing.updated_at = datetime.utcnow()

    return existing


def process_single_property(row: pd.Series) -> Optional[Property]:
    """
    Обрабатывает одну строку CSV и создает Property объект

    Args:
        row: Строка из DataFrame

    Returns:
        Property объект или None если ошибка
    """
    try:
        # 1. Извлечение данных из row
        mls_number = str(row.get('MLSNumber', row.get('MLS', '')))
        if not mls_number:
            return None

        address = str(row['Address'])
        city = str(row.get('City', 'Asheville'))
        state = str(row.get('State', 'NC'))
        zip_code = str(row.get('Zip', ''))

        # Извлечение URL (может быть в разных вариантах названия колонки)
        url = None
        for col_name in row.index:
            if 'URL' in col_name.upper():
                url = str(row[col_name]) if pd.notna(row[col_name]) else None
                break

        sale_price = pd.to_numeric(row.get('SalePrice'), errors='coerce')
        list_price = pd.to_numeric(row.get('ListPrice'), errors='coerce')
        sqft = pd.to_numeric(row.get('Sqft'), errors='coerce')

        # Пропустить записи без площади (для домов sqft обязателен)
        # Для земли sqft может быть пустым, но мы импортируем только дома
        if pd.isna(sqft) or sqft <= 0:
            return None

        status = str(row['Status']).lower().strip()
        bedrooms = pd.to_numeric(row.get('Bedrooms'), errors='coerce')
        bathrooms = pd.to_numeric(row.get('Bathrooms'), errors='coerce')
        lot_size = pd.to_numeric(row.get('LotSize'), errors='coerce')

        list_date = pd.to_datetime(row.get('ListDate'), errors='coerce')
        sale_date = pd.to_datetime(row.get('SaleDate'), errors='coerce')

        # 2. Нормализация статуса
        if status in ['sold', 'closed']:
            status = 'sold'
        elif status == 'active':
            status = 'active'
        elif status in ['pending', 'under contract', 'under_contract']:
            status = 'under_contract'
        elif status == 'withdrawn':
            status = 'withdrawn'

        # 3. Извлечение названия улицы
        street_name = extract_street_name(address)

        # 4. Геокодирование адреса (или использование из CSV)
        latitude = pd.to_numeric(row.get('Latitude'), errors='coerce')
        longitude = pd.to_numeric(row.get('Longitude'), errors='coerce')

        # Если координаты не в CSV - геокодировать
        if pd.isna(latitude) or pd.isna(longitude):
            full_address = f"{address}, {city}, {state} {zip_code}"
            coords = geocode_address(full_address)

            if coords:
                latitude, longitude = coords
            else:
                latitude, longitude = None, None
        else:
            latitude = float(latitude)
            longitude = float(longitude)

        # 5. Расчет метрик
        # Цена (приоритет sale_price, если нет - list_price)
        price = sale_price if pd.notna(sale_price) else list_price

        # Цена за sqft
        price_per_sqft_val = None
        if price and sqft:
            price_per_sqft_val = calculate_price_per_sqft(price, sqft)

        # Days on market
        days_on_market_val = None
        if list_date and pd.notna(list_date):
            days_on_market_val = calculate_days_on_market(
                list_date,
                sale_date if pd.notna(sale_date) else None
            )

        # 6. Создание Property объекта
        property_obj = Property(
            mls_number=mls_number,
            address=address,
            street_name=street_name,
            city=city,
            state=state,
            zip=zip_code if zip_code else None,
            latitude=latitude,
            longitude=longitude,
            sale_price=float(sale_price) if pd.notna(sale_price) else None,
            list_price=float(list_price) if pd.notna(list_price) else None,
            sqft=float(sqft),
            price_per_sqft=price_per_sqft_val,
            bedrooms=int(bedrooms) if pd.notna(bedrooms) else None,
            bathrooms=float(bathrooms) if pd.notna(bathrooms) else None,
            lot_size=float(lot_size) if pd.notna(lot_size) else None,
            status=status,
            list_date=list_date if pd.notna(list_date) else None,
            sale_date=sale_date if pd.notna(sale_date) else None,
            days_on_market=days_on_market_val,
            url=url,
            archived=False
        )

        return property_obj

    except Exception as e:
        print(f"Ошибка обработки строки: {e}")
        return None


def archive_old_properties() -> int:
    """
    Архивирует проданные дома старше ARCHIVE_SOLD_AFTER_DAYS дней

    Returns:
        Количество архивированных домов
    """
    session = get_session()
    try:
        # Вычислить дату отсечки
        cutoff_date = datetime.now() - timedelta(days=ARCHIVE_SOLD_AFTER_DAYS)

        # Найти старые проданные дома
        properties = session.query(Property).filter(
            Property.status == 'sold',
            Property.sale_date < cutoff_date,
            Property.archived == False
        ).all()

        # Архивировать
        count = 0
        for prop in properties:
            prop.archived = True
            count += 1

        session.commit()
        return count

    finally:
        session.close()


def import_csv_file(file_path: str) -> int:
    """
    Главная функция импорта CSV файла с домами

    Args:
        file_path: Путь к CSV файлу

    Returns:
        Количество новых добавленных домов
    """
    print(f"📥 Начинаю импорт: {file_path}")

    # 1. Загрузка CSV
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        print(f"✓ Загружено строк: {len(df)}")

        # Удалить строки, которые являются служебными сообщениями
        # (например, "In accordance with local MLS rules...")
        df = df[~df.iloc[:, 0].astype(str).str.contains('In accordance', na=False)]
        df = df.reset_index(drop=True)

    except Exception as e:
        print(f"❌ Ошибка чтения CSV: {e}")
        return 0

    # 1.5. Нормализация колонок Redfin (если это Redfin CSV)
    if 'ADDRESS' in df.columns or 'SQUARE FEET' in df.columns:
        print("Обнаружен формат Redfin CSV, нормализую колонки...")
        df = normalize_redfin_columns(df)
        print("✓ Колонки нормализованы")

    # 2. Валидация структуры
    if not validate_csv_structure(df):
        print("❌ Структура CSV невалидна")
        return 0

    print("✓ Структура CSV валидна")

    # 3. Счетчики
    new_count = 0
    updated_count = 0
    skipped_count = 0

    # 4. Получить сессию БД
    session = get_session()

    # 5. Обработка каждой строки
    try:
        for idx, row in df.iterrows():
            # Обработать строку
            property_obj = process_single_property(row)

            if property_obj is None:
                skipped_count += 1
                continue

            # Проверить на дубликат
            existing = check_duplicate(property_obj.mls_number)

            if existing:
                # Обновить статус и URL если изменился
                new_data = {
                    'status': property_obj.status,
                    'sale_date': property_obj.sale_date,
                    'sale_price': property_obj.sale_price,
                    'url': property_obj.url
                }
                update_property_status(session, property_obj.mls_number, new_data)
                updated_count += 1
            else:
                # Добавить новый
                session.add(property_obj)
                new_count += 1

            # Commit каждые 100 записей для производительности
            if (idx + 1) % 100 == 0:
                session.commit()
                print(f"  Обработано: {idx + 1}/{len(df)}")

        # Финальный commit
        session.commit()
        print("✓ Все данные сохранены в БД")

    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        session.rollback()
        return 0
    finally:
        session.close()

    # 6. Архивация старых данных
    print("📦 Архивирую старые данные...")
    archived_count = archive_old_properties()
    print(f"✓ Архивировано: {archived_count}")

    # 7. Итоговая статистика
    print(f"\n📊 СТАТИСТИКА ИМПОРТА:")
    print(f"  ✅ Новых домов добавлено: {new_count}")
    print(f"  🔄 Обновлено статусов: {updated_count}")
    print(f"  ⏭️  Пропущено (ошибки): {skipped_count}")
    print(f"  📦 Архивировано: {archived_count}")
    print(f"  📝 Всего обработано: {len(df)}")

    return new_count
