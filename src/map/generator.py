"""
Модуль генерации интерактивной карты с Folium
Создает базовую карту, добавляет слои, сохраняет в HTML
"""

import folium
from folium import Circle
import os
import sys

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CITY_CENTER, RADIUS_MILES


def create_base_map() -> folium.Map:
    """
    Создает базовую карту Folium с центром на Asheville

    Returns:
        folium.Map объект
    """
    # Создать карту с центром на CITY_CENTER
    base_map = folium.Map(
        location=[CITY_CENTER['lat'], CITY_CENTER['lon']],
        zoom_start=10,
        tiles='OpenStreetMap',
        control_scale=True
    )

    return base_map


def add_circle_radius(map_obj: folium.Map) -> None:
    """
    Добавляет круг радиуса RADIUS_MILES на карту

    Args:
        map_obj: Объект карты Folium
    """
    # Конвертировать мили в метры (1 миля = 1609.34 метра)
    radius_meters = RADIUS_MILES * 1609.34

    # Создать круг
    Circle(
        location=[CITY_CENTER['lat'], CITY_CENTER['lon']],
        radius=radius_meters,
        color='blue',
        fill=True,
        fillColor='lightblue',
        fillOpacity=0.1,
        weight=2,
        popup=f"{RADIUS_MILES} miles radius from {CITY_CENTER['name']}"
    ).add_to(map_obj)


def save_map(map_obj: folium.Map, filename: str = 'asheville_land_map.html') -> bool:
    """
    Сохраняет карту в HTML файл

    Args:
        map_obj: Объект карты Folium
        filename: Имя файла для сохранения

    Returns:
        True если успешно сохранено, False если ошибка
    """
    try:
        # Создать директорию output если не существует
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Полный путь к файлу
        filepath = os.path.join(output_dir, filename)

        # Сохранить карту
        map_obj.save(filepath)

        print(f"✅ Карта сохранена: {filepath}")
        return True

    except Exception as e:
        print(f"❌ Ошибка сохранения карты: {e}")
        return False


def generate_full_map() -> str:
    """
    Главная функция генерации полной карты с данными

    Returns:
        Путь к сохраненному файлу карты
    """
    print("🗺️  Начинаю генерацию карты...")

    # 1. Создать базовую карту
    map_obj = create_base_map()
    print("  ✓ Базовая карта создана")

    # 2. Добавить круг радиуса
    add_circle_radius(map_obj)
    print("  ✓ Радиус добавлен")

    # 3. Добавить слои с данными
    # (будет реализовано в layers.py и вызвано здесь)
    from map.layers import add_street_color_layer, add_land_opportunities_layer

    add_street_color_layer(map_obj)
    print("  ✓ Слой цветов улиц добавлен")

    add_land_opportunities_layer(map_obj)
    print("  ✓ Слой земельных участков добавлен")

    # 4. Сохранить карту
    filename = 'asheville_land_map.html'
    success = save_map(map_obj, filename)

    if success:
        filepath = os.path.join('output', filename)
        print(f"\n🎉 Карта успешно сгенерирована: {filepath}")
        return filepath
    else:
        return ''
