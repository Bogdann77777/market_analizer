"""
Модуль анализа перегрева рынка по ZIP кодам
Определяет статус рынка: cold, stable, growing, overheated
"""

from typing import Optional, Dict
from datetime import datetime, timedelta
import numpy as np
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Property, MarketHeatZone, get_session


def get_active_listings_count(zip_code: str) -> int:
    """
    Количество активных листингов в ZIP коде

    Args:
        zip_code: ZIP код

    Returns:
        Количество активных листингов
    """
    session = get_session()
    try:
        count = session.query(Property).filter(
            Property.zip == zip_code,
            Property.status == 'active',
            Property.archived == False
        ).count()
        return count
    finally:
        session.close()


def get_sold_last_90d_count(zip_code: str) -> int:
    """
    Количество продаж за последние 90 дней в ZIP коде

    Args:
        zip_code: ZIP код

    Returns:
        Количество продаж
    """
    session = get_session()
    try:
        ninety_days_ago = datetime.now() - timedelta(days=90)
        count = session.query(Property).filter(
            Property.zip == zip_code,
            Property.status == 'sold',
            Property.sale_date >= ninety_days_ago
        ).count()
        return count
    finally:
        session.close()


def calculate_inventory_months(active: int, sold_90d: int) -> float:
    """
    Рассчитывает месяцы инвентаря

    Args:
        active: Количество активных листингов
        sold_90d: Продано за 90 дней

    Returns:
        Месяцы инвентаря (999.0 если нет продаж)
    """
    if sold_90d == 0:
        return 999.0

    monthly_sales = sold_90d / 3.0  # 90 дней = 3 месяца

    if monthly_sales == 0:
        return 999.0

    inventory_months = active / monthly_sales
    return round(inventory_months, 1)


def determine_market_status(inventory: float, price_change: float, dom_change: float) -> str:
    """
    Определяет статус рынка на основе метрик

    Args:
        inventory: Месяцы инвентаря
        price_change: Изменение цен (%)
        dom_change: Изменение DOM (%)

    Returns:
        Статус: 'cold', 'stable', 'growing', 'overheated'
    """
    if inventory > 12:
        return 'cold'
    elif inventory >= 6:
        return 'stable'
    else:
        # Inventory < 6 месяцев
        if price_change > 15:
            return 'overheated'
        else:
            return 'growing'


def generate_recommendation(status: str) -> str:
    """
    Генерирует рекомендацию на основе статуса рынка

    Args:
        status: Статус рынка

    Returns:
        Рекомендация в текстовом виде
    """
    recommendations = {
        'cold': 'Выгодное время для покупки земли. Низкая конкуренция, покупатели имеют преимущество.',
        'stable': 'Хорошее время для инвестиций. Рынок сбалансирован.',
        'growing': 'Отличное время для покупки. Рынок растет, но без перегрева.',
        'overheated': 'ИЗБЕГАТЬ. Рынок перегрет. Высокий риск коррекции цен в ближайшие месяцы.'
    }

    return recommendations.get(status, 'Недостаточно данных для рекомендации.')


def calculate_price_change_90d(zip_code: str) -> float:
    """
    Рассчитывает изменение цен за 90 дней

    Args:
        zip_code: ZIP код

    Returns:
        Процент изменения цен (0.0 если недостаточно данных)
    """
    session = get_session()
    try:
        now = datetime.now()

        # Период 1: 90-60 дней назад
        period1_start = now - timedelta(days=90)
        period1_end = now - timedelta(days=60)

        properties_period1 = session.query(Property).filter(
            Property.zip == zip_code,
            Property.status == 'sold',
            Property.sale_date >= period1_start,
            Property.sale_date < period1_end,
            Property.price_per_sqft != None
        ).all()

        # Период 2: 30-0 дней назад (недавние)
        period2_start = now - timedelta(days=30)

        properties_period2 = session.query(Property).filter(
            Property.zip == zip_code,
            Property.status == 'sold',
            Property.sale_date >= period2_start,
            Property.price_per_sqft != None
        ).all()

        # Проверка достаточности данных
        if len(properties_period1) < 2 or len(properties_period2) < 2:
            return 0.0

        # Средняя цена за sqft в периоде 1
        avg_price_period1 = np.mean([p.price_per_sqft for p in properties_period1])

        # Средняя цена за sqft в периоде 2
        avg_price_period2 = np.mean([p.price_per_sqft for p in properties_period2])

        # Процент изменения
        if avg_price_period1 == 0:
            return 0.0

        change_percent = ((avg_price_period2 - avg_price_period1) / avg_price_period1) * 100
        return round(change_percent, 2)

    finally:
        session.close()


def calculate_dom_change(zip_code: str) -> float:
    """
    Рассчитывает изменение Days on Market за 90 дней

    Args:
        zip_code: ZIP код

    Returns:
        Процент изменения DOM (0.0 если недостаточно данных)
    """
    session = get_session()
    try:
        now = datetime.now()

        # Период 1: 90-60 дней назад
        period1_start = now - timedelta(days=90)
        period1_end = now - timedelta(days=60)

        properties_period1 = session.query(Property).filter(
            Property.zip == zip_code,
            Property.status == 'sold',
            Property.sale_date >= period1_start,
            Property.sale_date < period1_end,
            Property.days_on_market != None
        ).all()

        # Период 2: 30-0 дней назад (недавние)
        period2_start = now - timedelta(days=30)

        properties_period2 = session.query(Property).filter(
            Property.zip == zip_code,
            Property.status == 'sold',
            Property.sale_date >= period2_start,
            Property.days_on_market != None
        ).all()

        # Проверка достаточности данных
        if len(properties_period1) < 2 or len(properties_period2) < 2:
            return 0.0

        # Средний DOM в периоде 1
        avg_dom_period1 = np.mean([p.days_on_market for p in properties_period1])

        # Средний DOM в периоде 2
        avg_dom_period2 = np.mean([p.days_on_market for p in properties_period2])

        # Процент изменения
        if avg_dom_period1 == 0:
            return 0.0

        change_percent = ((avg_dom_period2 - avg_dom_period1) / avg_dom_period1) * 100
        return round(change_percent, 2)

    finally:
        session.close()


def analyze_market_heat_by_zip(zip_code: str) -> Optional[MarketHeatZone]:
    """
    Главная функция анализа перегрева рынка для ZIP кода

    Args:
        zip_code: ZIP код для анализа

    Returns:
        MarketHeatZone объект или None если недостаточно данных
    """
    # 1. Получить количество активных листингов
    active_count = get_active_listings_count(zip_code)

    # 2. Получить количество продаж за 90 дней
    sold_count = get_sold_last_90d_count(zip_code)

    # Проверка минимальных данных
    if sold_count == 0:
        return None

    # 3. Рассчитать месяцы инвентаря
    inventory_months = calculate_inventory_months(active_count, sold_count)

    # 4. Рассчитать изменение цен за 90 дней
    price_change = calculate_price_change_90d(zip_code)

    # 5. Рассчитать изменение DOM за 90 дней
    dom_change = calculate_dom_change(zip_code)

    # 6. Определить статус рынка
    market_status = determine_market_status(inventory_months, price_change, dom_change)

    # 7. Сгенерировать рекомендацию
    recommendation = generate_recommendation(market_status)

    # 8. Создать MarketHeatZone объект
    heat_zone = MarketHeatZone(
        zip_code=zip_code,
        active_listings=active_count,
        sold_last_90d=sold_count,
        inventory_months=inventory_months,
        price_change_90d=price_change,
        dom_change_90d=dom_change,
        market_status=market_status,
        recommendation=recommendation,
        last_updated=datetime.utcnow()
    )

    # 9. Сохранить в БД
    session = get_session()
    try:
        # Проверить существует ли запись для этого ZIP
        existing = session.query(MarketHeatZone).filter_by(zip_code=zip_code).first()

        if existing:
            # Обновить существующую
            existing.active_listings = active_count
            existing.sold_last_90d = sold_count
            existing.inventory_months = inventory_months
            existing.price_change_90d = price_change
            existing.dom_change_90d = dom_change
            existing.market_status = market_status
            existing.recommendation = recommendation
            existing.last_updated = datetime.utcnow()
            heat_zone = existing
        else:
            # Добавить новую
            session.add(heat_zone)

        session.commit()

    finally:
        session.close()

    # 10. Вернуть объект
    return heat_zone
