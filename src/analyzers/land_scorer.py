"""
Модуль оценки земельных участков и расчета urgency score
Фильтрует участки по критериям и присваивает баллы
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Property, StreetAnalysis, MarketHeatZone, LandOpportunity, get_session
from data.geocoder import haversine_distance
from config import LAND_FILTER, URGENCY_SCORING, URGENCY_LEVELS


def get_nearby_properties(lat: float, lon: float, radius_miles: float = 5.0) -> List[Property]:
    """
    Находит дома в радиусе от координат земельного участка

    Args:
        lat: Широта земельного участка
        lon: Долгота земельного участка
        radius_miles: Радиус поиска в милях (по умолчанию 5)

    Returns:
        Список домов в радиусе (проданные за год или активные)
    """
    session = get_session()
    try:
        one_year_ago = datetime.now() - timedelta(days=365)

        # Получить все дома с координатами
        all_properties = session.query(Property).filter(
            Property.latitude != None,
            Property.longitude != None,
            Property.archived == False
        ).all()

        # Фильтровать по расстоянию
        nearby = []
        for prop in all_properties:
            distance = haversine_distance(lat, lon, prop.latitude, prop.longitude)

            if distance <= radius_miles:
                # Приоритет: проданные за год
                if prop.status == 'sold' and prop.sale_date and prop.sale_date >= one_year_ago:
                    nearby.append(prop)
                # Или активные
                elif prop.status == 'active':
                    nearby.append(prop)

        return nearby

    finally:
        session.close()


def calculate_avg_nearby_price_sqft(properties: List[Property]) -> float:
    """
    Рассчитывает среднюю цену за sqft среди списка домов

    Args:
        properties: Список домов

    Returns:
        Средняя цена за sqft (0.0 если нет данных)
    """
    prices = [p.price_per_sqft for p in properties if p.price_per_sqft]

    if len(prices) == 0:
        return 0.0

    import numpy as np
    return float(np.mean(prices))


def count_recent_sales(properties: List[Property]) -> int:
    """
    Подсчитывает количество продаж за последние 90 дней

    Args:
        properties: Список домов

    Returns:
        Количество недавних продаж
    """
    ninety_days_ago = datetime.now() - timedelta(days=90)

    recent_sales = [
        p for p in properties
        if p.status == 'sold' and p.sale_date and p.sale_date >= ninety_days_ago
    ]

    return len(recent_sales)


def score_zone_color(color: str) -> int:
    """
    Присваивает баллы на основе цвета зоны

    Args:
        color: Цвет зоны ('green', 'light_green', 'yellow', 'red')

    Returns:
        Баллы от 0 до 100
    """
    color_scores = {
        'green': 100,
        'light_green': 75,
        'yellow': 50,
        'red': 0
    }

    return color_scores.get(color, 0)


def score_market_heat(status: str) -> int:
    """
    Присваивает баллы на основе статуса рынка

    Args:
        status: Статус рынка ('growing', 'stable', 'cold', 'overheated')

    Returns:
        Баллы от 0 до 100
    """
    heat_scores = {
        'growing': 100,
        'stable': 80,
        'cold': 50,
        'overheated': 0
    }

    return heat_scores.get(status, 0)


def score_price_opportunity(land_price_sqft: float, avg_nearby_price_sqft: float) -> int:
    """
    Оценивает выгодность цены земли по сравнению с соседними домами

    Args:
        land_price_sqft: Цена земли за sqft
        avg_nearby_price_sqft: Средняя цена соседних домов за sqft

    Returns:
        Баллы от 0 до 100
    """
    if avg_nearby_price_sqft == 0:
        return 0

    # Рассчитать процент от средней цены
    price_ratio = land_price_sqft / avg_nearby_price_sqft

    if price_ratio < 0.5:
        # Земля стоит < 50% от средней цены домов - отличная возможность
        return 100
    elif price_ratio < 0.7:
        # < 70% - хорошая возможность
        return 75
    elif price_ratio < 0.9:
        # < 90% - приемлемая возможность
        return 50
    else:
        # >= 90% - низкая выгодность
        return 0


def calculate_land_score(
    zone_color: str,
    market_status: str,
    nearby_avg_price_sqft: float,
    land_price_sqft: float,
    recent_sales_count: int
) -> int:
    """
    Рассчитывает общий urgency score для земельного участка

    Args:
        zone_color: Цвет зоны улицы
        market_status: Статус рынка ZIP кода
        nearby_avg_price_sqft: Средняя цена соседних домов за sqft
        land_price_sqft: Цена земли за sqft
        recent_sales_count: Количество продаж за 90 дней

    Returns:
        Общий балл от 0 до 100
    """
    # 1. Баллы за цвет зоны
    color_score = score_zone_color(zone_color)

    # 2. Баллы за статус рынка
    heat_score = score_market_heat(market_status)

    # 3. Баллы за выгодность цены
    price_score = score_price_opportunity(land_price_sqft, nearby_avg_price_sqft)

    # 4. Баллы за активность рынка (недавние продажи)
    if recent_sales_count >= 5:
        activity_score = 100
    elif recent_sales_count >= 3:
        activity_score = 75
    elif recent_sales_count >= 1:
        activity_score = 50
    else:
        activity_score = 0

    # 5. Взвешенная сумма на основе весов из config
    weights = URGENCY_SCORING
    total_score = (
        color_score * weights['zone_color'] +
        heat_score * weights['market_heat'] +
        price_score * weights['price_opportunity'] +
        activity_score * weights['recent_sales']
    )

    # Округлить до целого
    return int(round(total_score))


def evaluate_land_opportunity(property_obj: Property) -> Optional[LandOpportunity]:
    """
    Главная функция оценки земельного участка

    Args:
        property_obj: Property объект земельного участка

    Returns:
        LandOpportunity объект или None если не прошел фильтры
    """
    # 1. Проверить наличие координат
    if not property_obj.latitude or not property_obj.longitude:
        return None

    # 2. Получить анализ улицы для определения цвета зоны
    session = get_session()
    try:
        street_analysis = session.query(StreetAnalysis).filter_by(
            street_name=property_obj.street_name,
            city=property_obj.city
        ).first()

        if not street_analysis:
            # Нет анализа улицы - пропустить
            return None

        zone_color = street_analysis.color

        # 3. Получить анализ перегрева рынка для ZIP кода
        market_heat = session.query(MarketHeatZone).filter_by(
            zip_code=property_obj.zip
        ).first()

        if not market_heat:
            # Нет анализа рынка - пропустить
            return None

        market_status = market_heat.market_status

    finally:
        session.close()

    # 4. Применить фильтры из config.LAND_FILTER
    filters = LAND_FILTER

    # Проверить цену
    price = property_obj.list_price or property_obj.sale_price
    if not price or price > filters['max_price']:
        return None

    # Проверить размер участка
    if not property_obj.lot_size or property_obj.lot_size < filters['min_lot_size']:
        return None

    # Проверить цвет зоны
    if zone_color not in filters['allowed_zone_colors']:
        return None

    # Проверить статус рынка
    if market_status not in filters['market_heat_allowed']:
        return None

    # 5. Получить соседние дома
    nearby_properties = get_nearby_properties(
        property_obj.latitude,
        property_obj.longitude,
        radius_miles=5.0
    )

    if len(nearby_properties) == 0:
        # Нет соседних домов - недостаточно данных
        return None

    # 6. Рассчитать метрики
    avg_nearby_price_sqft = calculate_avg_nearby_price_sqft(nearby_properties)

    # Проверить минимальную цену соседей
    if avg_nearby_price_sqft < filters['min_nearby_price_sqft']:
        return None

    recent_sales_count = count_recent_sales(nearby_properties)

    # Проверить минимальное количество продаж
    if recent_sales_count < filters['min_recent_sales']:
        return None

    # Рассчитать цену земли за sqft
    if not property_obj.sqft or property_obj.sqft == 0:
        # Если нет sqft для дома, использовать lot_size
        # (для земли можно взять весь участок)
        land_sqft = property_obj.lot_size * 43560  # акры в sqft
        land_price_sqft = price / land_sqft if land_sqft > 0 else 0
    else:
        land_price_sqft = property_obj.price_per_sqft or (price / property_obj.sqft)

    # 7. Рассчитать urgency score
    urgency_score = calculate_land_score(
        zone_color=zone_color,
        market_status=market_status,
        nearby_avg_price_sqft=avg_nearby_price_sqft,
        land_price_sqft=land_price_sqft,
        recent_sales_count=recent_sales_count
    )

    # 8. Определить уровень срочности
    urgency_level = 'normal'
    if urgency_score >= URGENCY_LEVELS['urgent']:
        urgency_level = 'urgent'
    elif urgency_score >= URGENCY_LEVELS['good']:
        urgency_level = 'good'

    # 9. Создать LandOpportunity объект
    land_opp = LandOpportunity(
        property_id=property_obj.id,
        urgency_score=urgency_score,
        urgency_level=urgency_level,
        zone_color=zone_color,
        market_status=market_status,
        nearby_avg_price_sqft=avg_nearby_price_sqft,
        recent_sales_count=recent_sales_count,
        notes=f"Участок в {zone_color} зоне, рынок {market_status}",
        created_at=datetime.utcnow()
    )

    # 10. Сохранить в БД
    session = get_session()
    try:
        # Проверить существует ли уже запись для этого property_id
        existing = session.query(LandOpportunity).filter_by(
            property_id=property_obj.id
        ).first()

        if existing:
            # Обновить существующую
            existing.urgency_score = urgency_score
            existing.urgency_level = urgency_level
            existing.zone_color = zone_color
            existing.market_status = market_status
            existing.nearby_avg_price_sqft = avg_nearby_price_sqft
            existing.recent_sales_count = recent_sales_count
            existing.notes = land_opp.notes
            land_opp = existing
        else:
            # Добавить новую
            session.add(land_opp)

        session.commit()

    finally:
        session.close()

    # 11. Вернуть объект
    return land_opp
