"""
Модуль анализа улиц и присвоения цветов зонам
Рассчитывает метрики по домам на улице и определяет выгодность зоны
"""

from typing import List, Optional, Dict
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Property, StreetAnalysis, get_session
from config import COLOR_THRESHOLDS


def determine_color(avg_price_sqft: float) -> str:
    """
    Определяет цвет зоны на основе средней цены за sqft

    Args:
        avg_price_sqft: Средняя цена за квадратный фут

    Returns:
        Цвет зоны: 'green', 'light_green', 'yellow', 'red'
    """
    if avg_price_sqft >= COLOR_THRESHOLDS['green']:
        return 'green'
    elif avg_price_sqft >= COLOR_THRESHOLDS['light_green']:
        return 'light_green'
    elif avg_price_sqft >= COLOR_THRESHOLDS['yellow']:
        return 'yellow'
    else:
        return 'red'


def calculate_confidence(sample_size: int) -> float:
    """
    Рассчитывает уверенность в данных на основе размера выборки

    Args:
        sample_size: Количество домов в выборке

    Returns:
        Коэффициент уверенности от 0.0 до 1.0
        (10+ домов = 100% уверенность)
    """
    confidence = min(sample_size / 10.0, 1.0)
    return round(confidence, 2)


def get_properties_by_street(street_name: str, city: str) -> List[Property]:
    """
    Получает все дома на улице для анализа

    Args:
        street_name: Название улицы
        city: Город

    Returns:
        Список домов (приоритет - проданные за год, иначе активные)
    """
    session = get_session()
    try:
        one_year_ago = datetime.now() - timedelta(days=365)

        # Попытка 1: Проданные дома за последний год
        properties = session.query(Property).filter(
            Property.street_name == street_name,
            Property.city == city,
            Property.status == 'sold',
            Property.sale_date >= one_year_ago,
            Property.archived == False
        ).all()

        # Если достаточно данных (>= 3 дома)
        if len(properties) >= 3:
            return properties

        # Попытка 2: Активные листинги
        properties = session.query(Property).filter(
            Property.street_name == street_name,
            Property.city == city,
            Property.status == 'active',
            Property.archived == False
        ).all()

        return properties

    finally:
        session.close()


def calculate_street_metrics(properties: List[Property]) -> Dict:
    """
    Рассчитывает метрики для улицы на основе списка домов

    Args:
        properties: Список домов на улице

    Returns:
        Словарь с метриками: median/min/max price_per_sqft, avg/min/max DOM, sample_size
    """
    # Извлечь цены за sqft
    prices = [p.price_per_sqft for p in properties if p.price_per_sqft]

    if len(prices) == 0:
        return {}

    # Метрики цен
    metrics = {
        'median_price_sqft': float(np.median(prices)),
        'min_price_sqft': float(min(prices)),
        'max_price_sqft': float(max(prices)),
        'sample_size': len(properties)
    }

    # Извлечь Days On Market
    doms = [p.days_on_market for p in properties if p.days_on_market]

    if len(doms) > 0:
        metrics['avg_dom'] = float(np.mean(doms))
        metrics['min_dom'] = int(min(doms))
        metrics['max_dom'] = int(max(doms))
    else:
        metrics['avg_dom'] = None
        metrics['min_dom'] = None
        metrics['max_dom'] = None

    return metrics


def save_street_analysis(analysis: StreetAnalysis):
    """
    Сохраняет или обновляет анализ улицы в БД

    Args:
        analysis: Объект StreetAnalysis для сохранения
    """
    session = get_session()
    try:
        # Проверить существует ли запись
        existing = session.query(StreetAnalysis).filter_by(
            street_name=analysis.street_name,
            city=analysis.city
        ).first()

        if existing:
            # Обновить существующую
            existing.median_price_sqft = analysis.median_price_sqft
            existing.min_price_sqft = analysis.min_price_sqft
            existing.max_price_sqft = analysis.max_price_sqft
            existing.avg_dom = analysis.avg_dom
            existing.min_dom = analysis.min_dom
            existing.max_dom = analysis.max_dom
            existing.color = analysis.color
            existing.sample_size = analysis.sample_size
            existing.confidence_score = analysis.confidence_score
            existing.last_updated = datetime.utcnow()
        else:
            # Добавить новую
            session.add(analysis)

        session.commit()

    finally:
        session.close()


def analyze_single_street(street_name: str, city: str) -> Optional[StreetAnalysis]:
    """
    Анализирует одну улицу и возвращает StreetAnalysis объект

    Args:
        street_name: Название улицы
        city: Город

    Returns:
        StreetAnalysis объект или None если недостаточно данных
    """
    # 1. Получить дома на улице
    properties = get_properties_by_street(street_name, city)

    if len(properties) == 0:
        return None

    # 2. Рассчитать метрики
    metrics = calculate_street_metrics(properties)

    if not metrics:
        return None

    # 3. Определить цвет зоны
    color = determine_color(metrics['median_price_sqft'])

    # 4. Рассчитать confidence
    confidence = calculate_confidence(metrics['sample_size'])

    # 5. Создать StreetAnalysis объект
    analysis = StreetAnalysis(
        street_name=street_name,
        city=city,
        median_price_sqft=metrics['median_price_sqft'],
        min_price_sqft=metrics['min_price_sqft'],
        max_price_sqft=metrics['max_price_sqft'],
        avg_dom=metrics.get('avg_dom'),
        min_dom=metrics.get('min_dom'),
        max_dom=metrics.get('max_dom'),
        color=color,
        sample_size=metrics['sample_size'],
        confidence_score=confidence,
        last_updated=datetime.utcnow()
    )

    return analysis


def analyze_all_streets() -> List[StreetAnalysis]:
    """
    Анализирует все улицы в базе данных

    Returns:
        Список StreetAnalysis объектов
    """
    print("🔍 Начинаю анализ всех улиц...")

    session = get_session()
    try:
        # Получить список уникальных улиц
        street_city_pairs = session.query(
            Property.street_name,
            Property.city
        ).distinct().all()

        print(f"  Найдено улиц: {len(street_city_pairs)}")

    finally:
        session.close()

    # Счетчики по цветам
    color_counts = {'green': 0, 'light_green': 0, 'yellow': 0, 'red': 0}
    results = []

    # Анализировать каждую улицу
    for idx, (street_name, city) in enumerate(street_city_pairs, 1):
        analysis = analyze_single_street(street_name, city)

        if analysis:
            # Сохранить в БД
            save_street_analysis(analysis)
            results.append(analysis)

            # Обновить счетчики
            color_counts[analysis.color] += 1

        # Вывод прогресса каждые 50 улиц
        if idx % 50 == 0:
            print(f"  Обработано: {idx}/{len(street_city_pairs)}")

    # Итоговая статистика
    print(f"\n📊 СТАТИСТИКА АНАЛИЗА УЛИЦ:")
    print(f"  Обработано улиц: {len(street_city_pairs)}")
    print(f"  🟢 Зеленых: {color_counts['green']} ({color_counts['green']*100//len(results) if results else 0}%)")
    print(f"  🟢 Светло-зеленых: {color_counts['light_green']} ({color_counts['light_green']*100//len(results) if results else 0}%)")
    print(f"  🟡 Желтых: {color_counts['yellow']} ({color_counts['yellow']*100//len(results) if results else 0}%)")
    print(f"  🔴 Красных: {color_counts['red']} ({color_counts['red']*100//len(results) if results else 0}%)")

    return results
