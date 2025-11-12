"""
Модуль создания слоев карты
Добавляет маркеры домов, земли, цветовые зоны
"""

import folium
from folium import Marker, Icon, FeatureGroup
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Property, StreetAnalysis, LandOpportunity, get_session
from map.popups import create_property_popup, create_land_opportunity_popup


def add_street_color_layer(map_obj: folium.Map) -> None:
    """
    Добавляет слой с домами, раскрашенными по цвету зоны

    Args:
        map_obj: Объект карты Folium
    """
    session = get_session()
    try:
        # Получить все анализы улиц
        street_analyses = session.query(StreetAnalysis).all()

        # Создать feature groups для каждого цвета
        green_group = FeatureGroup(name='🟢 Green Zones ($350+ /sqft)')
        light_green_group = FeatureGroup(name='🟢 Light Green ($300-350 /sqft)')
        yellow_group = FeatureGroup(name='🟡 Yellow Zones ($220-300 /sqft)')
        red_group = FeatureGroup(name='🔴 Red Zones (<$220 /sqft)')

        # Маппинг цветов к группам
        color_groups = {
            'green': green_group,
            'light_green': light_green_group,
            'yellow': yellow_group,
            'red': red_group
        }

        # Маппинг цветов к иконкам Folium
        color_icons = {
            'green': 'green',
            'light_green': 'lightgreen',
            'yellow': 'orange',
            'red': 'red'
        }

        # Для каждой улицы получить дома и добавить маркеры
        for street in street_analyses:
            # Получить дома на этой улице с координатами (только активные листинги)
            properties = session.query(Property).filter(
                Property.street_name == street.street_name,
                Property.city == street.city,
                Property.latitude != None,
                Property.longitude != None,
                Property.archived == False,
                Property.status.in_(['active', 'Active', 'ACTIVE'])  # Only active listings
            ).limit(10).all()  # Ограничить до 10 домов на улицу для производительности

            # Добавить маркер для каждого дома
            for prop in properties:
                # Создать popup с информацией
                popup_html = create_property_popup(prop, street.color)

                # Определить группу и цвет иконки
                group = color_groups.get(street.color)
                icon_color = color_icons.get(street.color, 'gray')

                if group:
                    # Создать маркер
                    Marker(
                        location=[prop.latitude, prop.longitude],
                        popup=folium.Popup(popup_html, max_width=300),
                        icon=Icon(color=icon_color, icon='home', prefix='fa'),
                        tooltip=f"{prop.address} - {street.color} zone"
                    ).add_to(group)

        # Добавить все группы на карту
        green_group.add_to(map_obj)
        light_green_group.add_to(map_obj)
        yellow_group.add_to(map_obj)
        red_group.add_to(map_obj)

    finally:
        session.close()


def add_land_opportunities_layer(map_obj: folium.Map) -> None:
    """
    Добавляет слой с земельными участками (возможностями)

    Args:
        map_obj: Объект карты Folium
    """
    session = get_session()
    try:
        # Получить все земельные возможности
        opportunities = session.query(LandOpportunity).all()

        # Создать feature groups по уровню срочности
        urgent_group = FeatureGroup(name='🔥 Urgent Land (Score ≥80)')
        good_group = FeatureGroup(name='⭐ Good Land (Score 50-79)')
        normal_group = FeatureGroup(name='✅ Normal Land (Score <50)')

        # Маппинг уровней к группам
        urgency_groups = {
            'urgent': urgent_group,
            'good': good_group,
            'normal': normal_group
        }

        # Маппинг уровней к цветам иконок
        urgency_icons = {
            'urgent': ('red', 'star'),
            'good': ('orange', 'flag'),
            'normal': ('blue', 'info-sign')
        }

        # Для каждой возможности добавить маркер
        for opp in opportunities:
            # Получить связанный Property объект (только активные листинги)
            prop = session.query(Property).filter(
                Property.id == opp.property_id,
                Property.status.in_(['active', 'Active', 'ACTIVE'])  # Only active listings
            ).first()

            if not prop or not prop.latitude or not prop.longitude:
                continue

            # Создать popup с информацией
            popup_html = create_land_opportunity_popup(prop, opp)

            # Определить группу и иконку
            group = urgency_groups.get(opp.urgency_level, normal_group)
            icon_color, icon_symbol = urgency_icons.get(opp.urgency_level, ('blue', 'info-sign'))

            # Создать маркер
            Marker(
                location=[prop.latitude, prop.longitude],
                popup=folium.Popup(popup_html, max_width=350),
                icon=Icon(color=icon_color, icon=icon_symbol, prefix='glyphicon'),
                tooltip=f"LAND: {prop.address} - Score {opp.urgency_score}"
            ).add_to(group)

        # Добавить все группы на карту
        urgent_group.add_to(map_obj)
        good_group.add_to(map_obj)
        normal_group.add_to(map_obj)

        # Добавить контроль слоев
        folium.LayerControl(collapsed=False).add_to(map_obj)

    finally:
        session.close()


def add_market_heat_layer(map_obj: folium.Map) -> None:
    """
    Добавляет слой с тепловой картой рынка по ZIP кодам (опционально)

    Args:
        map_obj: Объект карты Folium
    """
    # Эта функция может быть реализована позже для визуализации ZIP зон
    # Пока оставляем заглушку
    pass
