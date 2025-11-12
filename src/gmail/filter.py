"""
Модуль фильтрации писем о земельных участках
Проверяет критерии, выбирает подходящие предложения
"""

from typing import List, Dict
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LAND_FILTER
from gmail.gmail_client import fetch_unread_emails, get_email_body
from gmail.parser import parse_land_email


def is_land_opportunity_email(subject: str, from_email: str) -> bool:
    """
    Определяет является ли письмо предложением земли

    Args:
        subject: Тема письма
        from_email: Email отправителя

    Returns:
        True если письмо о земле, False иначе
    """
    # Ключевые слова в теме письма
    land_keywords = [
        'land',
        'lot',
        'acre',
        'property',
        'parcel',
        'vacant',
        'buildable',
        'homesite'
    ]

    # Проверить тему на наличие ключевых слов
    subject_lower = subject.lower()
    has_keyword = any(keyword in subject_lower for keyword in land_keywords)

    # Проверить отправителя (известные MLS агенты или домены)
    trusted_domains = [
        'mls.com',
        'realtor.com',
        'zillow.com',
        'redfin.com',
        'canopy.realtysouth.com'
    ]

    from_email_lower = from_email.lower()
    from_trusted = any(domain in from_email_lower for domain in trusted_domains)

    # Письмо проходит если есть ключевое слово И от доверенного источника
    return has_keyword and from_trusted


def meets_criteria(parsed_data: Dict) -> bool:
    """
    Проверяет соответствие данных критериям фильтра

    Args:
        parsed_data: Словарь с данными земли из parse_land_email()

    Returns:
        True если соответствует критериям, False иначе
    """
    filters = LAND_FILTER

    # 1. Проверить наличие обязательных полей
    if not parsed_data.get('address'):
        return False

    # 2. Проверить цену
    price = parsed_data.get('price')
    if price is None:
        # Цена не указана - пропустить
        return False

    if price > filters['max_price']:
        # Слишком дорого
        return False

    # 3. Проверить размер участка
    lot_size = parsed_data.get('lot_size')
    if lot_size is None:
        # Размер не указан - пропустить
        return False

    if lot_size < filters['min_lot_size']:
        # Слишком маленький участок
        return False

    # Все критерии пройдены
    return True


def filter_land_emails(service) -> List[Dict]:
    """
    Главная функция фильтрации писем о земле

    Args:
        service: Gmail API service объект

    Returns:
        Список подходящих предложений с данными:
        [
            {
                'email_id': str,
                'subject': str,
                'from': str,
                'date': str,
                'parsed_data': Dict (address, price, lot_size, mls_number)
            }
        ]
    """
    qualified_opportunities = []

    # 1. Получить непрочитанные письма
    unread_emails = fetch_unread_emails(service, query='is:unread')

    print(f"📧 Найдено непрочитанных писем: {len(unread_emails)}")

    # 2. Фильтровать каждое письмо
    for email_meta in unread_emails:
        email_id = email_meta['id']
        subject = email_meta['subject']
        from_email = email_meta['from']
        date = email_meta['date']

        # Проверить является ли это письмо о земле
        if not is_land_opportunity_email(subject, from_email):
            continue

        # 3. Получить тело письма
        body = get_email_body(service, email_id)

        if not body:
            continue

        # 4. Парсить данные земли
        parsed_data = parse_land_email(body)

        # 5. Проверить соответствие критериям
        if not meets_criteria(parsed_data):
            continue

        # 6. Добавить в список подходящих
        qualified_opportunities.append({
            'email_id': email_id,
            'subject': subject,
            'from': from_email,
            'date': date,
            'parsed_data': parsed_data
        })

        print(f"  ✅ Найдена возможность: {parsed_data['address']} - ${parsed_data['price']:,.0f}")

    print(f"\n📊 Подходящих предложений: {len(qualified_opportunities)}")

    return qualified_opportunities
