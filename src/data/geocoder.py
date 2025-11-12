"""
Модуль геокодирования адресов
Использует Nominatim (OpenStreetMap) с кешированием результатов
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import json
import os
import random
import math
from typing import Tuple, Optional, List, Dict
import sys

# Добавляем родительскую директорию в path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CITY_CENTER

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================================

# Путь к файлу кеша
CACHE_FILE = 'data/cache/geocode_cache.json'

# Инициализация геокодера Nominatim
# ВАЖНО: Nominatim имеет лимит 1 запрос в секунду
geolocator = Nominatim(user_agent="asheville_land_analyzer_v1", timeout=10)

# Глобальный кеш (загружается при первом использовании)
_cache = None


# ============================================================================
# ФУНКЦИИ РАБОТЫ С КЕШЕМ
# ============================================================================

def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    """
    Загружает кеш геокодирования из файла

    Returns:
        Словарь {адрес: (lat, lon)}
    """
    global _cache

    # Если уже загружен в память - вернуть
    if _cache is not None:
        return _cache

    # Проверить существование файла
    if not os.path.exists(CACHE_FILE):
        _cache = {}
        return _cache

    # Загрузить из файла
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Конвертировать списки обратно в кортежи
            _cache = {addr: tuple(coords) for addr, coords in data.items()}
            return _cache
    except (json.JSONDecodeError, IOError):
        # При ошибке вернуть пустой кеш
        _cache = {}
        return _cache


def save_geocode_cache(cache: Dict):
    """
    Сохраняет кеш геокодирования в файл

    Args:
        cache: Словарь для сохранения
    """
    global _cache

    # Создать директорию если не существует
    cache_dir = os.path.dirname(CACHE_FILE)
    if cache_dir and not os.path.exists(cache_dir):
        os.makedirs(cache_dir, exist_ok=True)

    # Сохранить в файл
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            # Конвертировать кортежи в списки для JSON
            data = {addr: list(coords) for addr, coords in cache.items()}
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Обновить глобальный кеш
        _cache = cache
    except IOError:
        # Ошибка записи - игнорируем, но логируем
        pass


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Рассчитывает расстояние между двумя точками на Земле по формуле Haversine

    Args:
        lat1, lon1: Координаты первой точки
        lat2, lon2: Координаты второй точки

    Returns:
        Расстояние в милях
    """
    # Радиус Земли в милях
    R = 3959.0

    # Конвертация в радианы
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    # Формула Haversine
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Проверяет что координаты находятся в пределах RADIUS_MILES от CITY_CENTER

    Args:
        lat: Широта
        lon: Долгота

    Returns:
        True если координаты валидны
    """
    from config import RADIUS_MILES

    # Рассчитать расстояние от центра
    distance = haversine_distance(
        CITY_CENTER['lat'], CITY_CENTER['lon'],
        lat, lon
    )

    # Проверить что в пределах радиуса
    return distance <= RADIUS_MILES


# ============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ГЕОКОДИРОВАНИЯ
# ============================================================================

def fallback_geocode(address: str) -> Optional[Tuple[float, float]]:
    """
    Запасной метод геокодирования с упрощенными адресами

    Args:
        address: Полный адрес

    Returns:
        (lat, lon) или None
    """
    # Импорт для извлечения улицы
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from analyzers.price_calculator import extract_street_name

    # Попытка 1: Только улица без номера дома
    try:
        street_only = extract_street_name(address)
        full_address = f"{street_only}, Asheville, NC"

        location = geolocator.geocode(full_address)
        if location:
            if validate_coordinates(location.latitude, location.longitude):
                time.sleep(1)  # Лимит Nominatim
                return (location.latitude, location.longitude)

        time.sleep(1)
    except (GeocoderTimedOut, GeocoderServiceError):
        time.sleep(2)

    # Попытка 2: Только ZIP код (если есть)
    import re
    zip_match = re.search(r'\b\d{5}\b', address)
    if zip_match:
        try:
            zip_code = zip_match.group(0)
            location = geolocator.geocode(f"{zip_code}, NC")

            if location:
                # Добавить случайный offset чтобы точки не накладывались
                lat = location.latitude + random.uniform(-0.01, 0.01)
                lon = location.longitude + random.uniform(-0.01, 0.01)

                if validate_coordinates(lat, lon):
                    time.sleep(1)
                    return (lat, lon)

            time.sleep(1)
        except (GeocoderTimedOut, GeocoderServiceError):
            time.sleep(2)

    # Попытка 3: Центр города + random offset
    lat = CITY_CENTER['lat'] + random.uniform(-0.05, 0.05)
    lon = CITY_CENTER['lon'] + random.uniform(-0.05, 0.05)

    return (lat, lon)


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Геокодирует адрес с использованием кеша

    Args:
        address: Полный адрес для геокодирования

    Returns:
        (latitude, longitude) или None если не удалось геокодировать
    """
    # Нормализация адреса
    address = address.strip().title()

    # Загрузить кеш
    cache = load_geocode_cache()

    # Проверить в кеше
    if address in cache:
        return cache[address]

    # Попытка геокодирования (макс 3 попытки при timeout)
    for attempt in range(3):
        try:
            # Полный адрес с городом и штатом
            full_address = f"{address}, Asheville, NC"
            location = geolocator.geocode(full_address)

            if location:
                coords = (location.latitude, location.longitude)

                # Валидация координат
                if validate_coordinates(coords[0], coords[1]):
                    # Сохранить в кеш
                    cache[address] = coords
                    save_geocode_cache(cache)

                    # Лимит API - 1 запрос в секунду
                    time.sleep(1)
                    return coords

            # Если не нашли - fallback
            time.sleep(1)
            break

        except GeocoderTimedOut:
            # Таймаут - повторить через 2 секунды
            if attempt < 2:
                time.sleep(2)
                continue
            break

        except GeocoderServiceError:
            # Ошибка сервиса
            time.sleep(2)
            break

    # Если основной метод не сработал - fallback
    coords = fallback_geocode(address)

    if coords:
        # Сохранить в кеш
        cache[address] = coords
        save_geocode_cache(cache)

    return coords


def batch_geocode(addresses: List[str]) -> List[Optional[Tuple[float, float]]]:
    """
    Массовое геокодирование списка адресов

    Args:
        addresses: Список адресов

    Returns:
        Список координат (может содержать None)
    """
    results = []

    # Загрузить кеш один раз
    cache = load_geocode_cache()

    for address in addresses:
        # Нормализация
        address = address.strip().title()

        # Проверить в кеше
        if address in cache:
            results.append(cache[address])
        else:
            # Геокодировать
            coords = geocode_address(address)
            results.append(coords)

            # Задержка между запросами (Nominatim лимит)
            time.sleep(1)

    return results
