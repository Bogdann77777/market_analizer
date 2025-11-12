"""
Модуль расчета цен и метрик недвижимости
Чистые функции без зависимостей от других модулей
"""

from datetime import datetime
from typing import Optional
import re


def calculate_price_per_sqft(price: float, sqft: float) -> Optional[float]:
    """
    Рассчитывает цену за квадратный фут

    Args:
        price: Цена недвижимости ($)
        sqft: Площадь (square feet)

    Returns:
        Цена за sqft округленная до 2 знаков, или None если невозможно рассчитать
    """
    # Проверка на валидность данных
    if sqft <= 0 or price <= 0:
        return None

    # Расчет и округление до 2 знаков
    result = price / sqft
    return round(result, 2)


def calculate_days_on_market(list_date: datetime, sale_date: Optional[datetime] = None) -> int:
    """
    Рассчитывает количество дней на рынке (DOM - Days On Market)

    Args:
        list_date: Дата выставления на продажу
        sale_date: Дата продажи (None если еще не продан)

    Returns:
        Количество дней на рынке
    """
    # Если продан - разница между датами продажи и выставления
    if sale_date:
        delta = sale_date - list_date
        return max(delta.days, 0)  # Не может быть отрицательным

    # Если не продан - разница между сегодня и датой выставления
    today = datetime.now()
    delta = today - list_date
    return max(delta.days, 0)


def extract_street_name(address: str) -> str:
    """
    Извлекает название улицы из полного адреса
    Удаляет номер дома, город, штат, ZIP

    Args:
        address: Полный адрес ("123 Main Street, Asheville, NC 28801")

    Returns:
        Название улицы ("Main Street")
    """
    # Убираем лишние пробелы
    address = address.strip()

    # Убираем город, штат, ZIP (все после запятой)
    if ',' in address:
        address = address.split(',')[0]

    # Убираем номер дома в начале (один или несколько цифр и пробел)
    address = re.sub(r'^\d+\s+', '', address)

    return address.strip()


def format_currency(amount: float) -> str:
    """
    Форматирует число как валюту с запятыми и знаком доллара

    Args:
        amount: Сумма в долларах

    Returns:
        Отформатированная строка ("$450,000")
    """
    # Округляем до целых
    amount_int = int(round(amount))

    # Форматируем с запятыми и добавляем знак $
    return f"${amount_int:,}"


def calculate_price_change(old_price: float, new_price: float) -> float:
    """
    Рассчитывает процентное изменение цены

    Args:
        old_price: Старая цена
        new_price: Новая цена

    Returns:
        Процент изменения (положительный = рост, отрицательный = падение)
    """
    # Проверка деления на ноль
    if old_price == 0:
        return 0.0

    # Расчет процентного изменения
    change = ((new_price - old_price) / old_price) * 100

    # Округление до 1 знака
    return round(change, 1)
