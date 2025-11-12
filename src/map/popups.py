"""
Модуль генерации HTML popups для маркеров карты
Создает красивые информационные окна для домов и земли
"""

from typing import Optional
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database import Property, LandOpportunity
from analyzers.price_calculator import format_currency


def create_property_popup(property: Property, zone_color: str) -> str:
    """
    Создает HTML popup для маркера дома

    Args:
        property: Property объект
        zone_color: Цвет зоны ('green', 'light_green', 'yellow', 'red')

    Returns:
        HTML строка для popup
    """
    # Определить emoji для цвета
    color_emoji = {
        'green': '🟢',
        'light_green': '🟢',
        'yellow': '🟡',
        'red': '🔴'
    }
    emoji = color_emoji.get(zone_color, '⚪')

    # Форматировать цену
    price = property.sale_price or property.list_price
    price_str = format_currency(price) if price else 'N/A'

    # Форматировать price_per_sqft
    price_sqft_str = f"${property.price_per_sqft:.2f}/sqft" if property.price_per_sqft else 'N/A'

    # Статус
    status_emoji = {
        'active': '🟢 Active',
        'sold': '✅ Sold',
        'under_contract': '🔶 Under Contract',
        'withdrawn': '⛔ Withdrawn'
    }
    status_str = status_emoji.get(property.status, property.status.upper())

    # Создать HTML
    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: #333;">
            {emoji} {zone_color.replace('_', ' ').title()} Zone
        </h4>
        <p style="margin: 5px 0; font-size: 13px;">
            <b>Address:</b> {property.address}<br>
            <b>City:</b> {property.city}, {property.state}<br>
            <b>Price:</b> {price_str}<br>
            <b>Sqft:</b> {property.sqft:,.0f} sqft<br>
            <b>Price/sqft:</b> {price_sqft_str}<br>
            <b>Status:</b> {status_str}<br>
    """

    # Добавить ссылку на листинг если есть
    if property.url:
        html += f"""
            <b>Listing:</b> <a href="{property.url}" target="_blank" style="color: #0066cc; text-decoration: underline;">View on Redfin</a><br>
        """

    html += """
        </p>
    """

    # Добавить дополнительные поля если есть
    if property.bedrooms or property.bathrooms:
        html += f"""
        <p style="margin: 5px 0; font-size: 13px;">
            <b>Beds/Baths:</b> {property.bedrooms or 'N/A'} / {property.bathrooms or 'N/A'}
        </p>
        """

    if property.lot_size:
        html += f"""
        <p style="margin: 5px 0; font-size: 13px;">
            <b>Lot Size:</b> {property.lot_size:.2f} acres
        </p>
        """

    if property.days_on_market:
        html += f"""
        <p style="margin: 5px 0; font-size: 13px;">
            <b>Days on Market:</b> {property.days_on_market}
        </p>
        """

    html += "</div>"

    return html


def create_land_opportunity_popup(property: Property, land_opp: LandOpportunity) -> str:
    """
    Создает HTML popup для маркера земельного участка

    Args:
        property: Property объект
        land_opp: LandOpportunity объект

    Returns:
        HTML строка для popup
    """
    # Определить emoji для urgency level
    urgency_emoji = {
        'urgent': '🔥 URGENT',
        'good': '⭐ GOOD',
        'normal': '✅ Normal'
    }
    urgency_str = urgency_emoji.get(land_opp.urgency_level, '✅ Normal')

    # Определить цвет фона для urgency
    urgency_colors = {
        'urgent': '#ffcccc',
        'good': '#fff4cc',
        'normal': '#e6f7ff'
    }
    bg_color = urgency_colors.get(land_opp.urgency_level, '#ffffff')

    # Форматировать цену
    price = property.list_price or property.sale_price
    price_str = format_currency(price) if price else 'N/A'

    # Форматировать lot size
    lot_size_str = f"{property.lot_size:.2f} acres" if property.lot_size else 'N/A'

    # Форматировать nearby avg price
    nearby_price_str = f"${land_opp.nearby_avg_price_sqft:.2f}/sqft" if land_opp.nearby_avg_price_sqft else 'N/A'

    # Создать HTML
    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 300px; background-color: {bg_color}; padding: 10px; border-radius: 5px;">
        <h3 style="margin: 0 0 10px 0; color: #d9534f;">
            {urgency_str}
        </h3>
        <h4 style="margin: 0 0 10px 0; color: #333;">
            Score: {land_opp.urgency_score}/100
        </h4>
        <p style="margin: 5px 0; font-size: 13px;">
            <b>Address:</b> {property.address}<br>
            <b>City:</b> {property.city}, {property.state} {property.zip}<br>
            <b>Price:</b> {price_str}<br>
            <b>Lot Size:</b> {lot_size_str}<br>
    """

    # Добавить ссылку на листинг если есть
    if land_opp.url:
        html += f"""
            <b>Listing:</b> <a href="{land_opp.url}" target="_blank" style="color: #0066cc; text-decoration: underline;">View on Redfin</a><br>
        """

    html += f"""
        </p>
        <hr style="margin: 10px 0; border: none; border-top: 1px solid #ddd;">
        <p style="margin: 5px 0; font-size: 12px; color: #555;">
            <b>Zone Color:</b> {land_opp.zone_color.replace('_', ' ').title()}<br>
            <b>Market Status:</b> {land_opp.market_status.title()}<br>
            <b>Nearby Avg Price:</b> {nearby_price_str}<br>
            <b>Recent Sales (90d):</b> {land_opp.recent_sales_count}<br>
        </p>
        <p style="margin: 10px 0 0 0; font-size: 12px; font-style: italic; color: #666;">
            {land_opp.notes}
        </p>
    </div>
    """

    return html
