"""
Модуль парсинга писем от MLS агентов
Извлекает адрес, цену, размер участка, MLS номер
"""

import re
from typing import Optional, Dict


def extract_address_from_email(body: str) -> Optional[str]:
    """
    Извлекает адрес из текста письма

    Args:
        body: Текст письма

    Returns:
        Адрес или None если не найден
    """
    # Паттерны для поиска адресов
    # Формат: "123 Main Street, Asheville, NC 28801"
    patterns = [
        r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Way|Court|Ct|Circle|Cir|Place|Pl),?\s+[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5})',
        r'Address:\s*(.+?)(?:\n|$)',
        r'Property:\s*(.+?)(?:\n|$)',
        r'Location:\s*(.+?)(?:\n|$)'
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            # Очистить от лишних символов
            address = re.sub(r'\s+', ' ', address)
            return address

    return None


def extract_price_from_email(body: str) -> Optional[float]:
    """
    Извлекает цену из текста письма

    Args:
        body: Текст письма

    Returns:
        Цена в долларах или None если не найдена
    """
    # Паттерны для поиска цен
    # Формат: "$150,000" или "$150.000" или "Price: $150000"
    patterns = [
        r'\$\s*([\d,]+(?:\.\d{2})?)',
        r'Price:\s*\$?\s*([\d,]+)',
        r'List Price:\s*\$?\s*([\d,]+)',
        r'Sale Price:\s*\$?\s*([\d,]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            price_str = match.group(1)
            # Удалить запятые
            price_str = price_str.replace(',', '')
            try:
                price = float(price_str)
                # Проверить разумность цены (от $1,000 до $10,000,000)
                if 1000 <= price <= 10000000:
                    return price
            except ValueError:
                continue

    return None


def extract_lot_size_from_email(body: str) -> Optional[float]:
    """
    Извлекает размер участка из текста письма

    Args:
        body: Текст письма

    Returns:
        Размер участка в акрах или None если не найден
    """
    # Паттерны для поиска размера участка
    # Формат: "5.5 acres" или "5 acres" или "Lot: 5.5 ac"
    patterns = [
        r'([\d.]+)\s*acres?',
        r'Lot[:\s]+(\d+\.?\d*)\s*ac',
        r'Land:\s*([\d.]+)\s*acres?',
        r'Acreage:\s*([\d.]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            lot_str = match.group(1)
            try:
                lot_size = float(lot_str)
                # Проверить разумность размера (от 0.1 до 1000 акров)
                if 0.1 <= lot_size <= 1000:
                    return lot_size
            except ValueError:
                continue

    return None


def extract_mls_number_from_email(body: str) -> Optional[str]:
    """
    Извлекает MLS номер из текста письма

    Args:
        body: Текст письма

    Returns:
        MLS номер или None если не найден
    """
    # Паттерны для поиска MLS номера
    # Формат: "MLS# 12345" или "MLS: 12345" или "MLS #12345"
    patterns = [
        r'MLS\s*#?\s*[:\s]*(\w+)',
        r'MLS Number:\s*(\w+)',
        r'Listing ID:\s*(\w+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            mls_number = match.group(1).strip()
            return mls_number

    return None


def parse_land_email(body: str) -> Dict:
    """
    Главная функция парсинга письма о земельном участке

    Args:
        body: Текст письма

    Returns:
        Словарь с извлеченными полями:
        {
            'address': str or None,
            'price': float or None,
            'lot_size': float or None,
            'mls_number': str or None
        }
    """
    # Извлечь все поля
    address = extract_address_from_email(body)
    price = extract_price_from_email(body)
    lot_size = extract_lot_size_from_email(body)
    mls_number = extract_mls_number_from_email(body)

    # Собрать результат
    result = {
        'address': address,
        'price': price,
        'lot_size': lot_size,
        'mls_number': mls_number
    }

    return result
