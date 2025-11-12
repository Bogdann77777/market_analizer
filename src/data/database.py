"""
Модели базы данных и ORM для проекта Asheville Land Analyzer
Использует SQLAlchemy для работы с PostgreSQL
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import sys
import os

# Добавляем родительскую директорию в path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

# ============================================================================
# SQLALCHEMY SETUP
# ============================================================================

# Базовый класс для всех моделей
Base = declarative_base()

# Engine с настройками подключения
# pool_pre_ping=True для автопереподключения при потере соединения
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Не логировать SQL запросы
    pool_pre_ping=True  # Проверять соединение перед использованием
)

# Фабрика сессий
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ============================================================================
# МОДЕЛИ БАЗЫ ДАННЫХ
# ============================================================================

class Property(Base):
    """
    Модель дома/недвижимости из MLS
    Хранит все данные о домах: адрес, цены, характеристики, статус
    """
    __tablename__ = 'properties'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Идентификаторы
    mls_number = Column(String(50), unique=True, nullable=False, index=True)

    # Адрес
    address = Column(String(500), nullable=False)
    street_name = Column(String(200), index=True)  # Извлекается из address
    city = Column(String(100), nullable=False)
    state = Column(String(2), default='NC')
    zip = Column(String(10), index=True)

    # Координаты
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Цены
    sale_price = Column(Float, nullable=True)
    list_price = Column(Float, nullable=True)
    sqft = Column(Float, nullable=False)
    price_per_sqft = Column(Float, nullable=True, index=True)  # Рассчитывается

    # Характеристики
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)
    lot_size = Column(Float, nullable=True)  # acres

    # Статус (active, sold, under_contract, pending, withdrawn)
    status = Column(String(50), nullable=False, index=True)

    # Даты
    list_date = Column(DateTime, nullable=True)
    sale_date = Column(DateTime, nullable=True)
    days_on_market = Column(Integer, nullable=True)  # Рассчитывается

    # URL листинга
    url = Column(String(500), nullable=True)

    # Служебные поля
    archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Индексы для быстрого поиска
    __table_args__ = (
        Index('idx_location', 'latitude', 'longitude'),
        Index('idx_street_city', 'street_name', 'city'),
        Index('idx_status_date', 'status', 'sale_date'),
    )


class StreetAnalysis(Base):
    """
    Модель анализа улицы
    Хранит результаты анализа: средние цены, DOM, цвет зоны
    """
    __tablename__ = 'street_analysis'

    id = Column(Integer, primary_key=True, autoincrement=True)
    street_name = Column(String(200), nullable=False, index=True)
    city = Column(String(100), nullable=False)

    # Метрики цен ($/sqft)
    median_price_sqft = Column(Float, nullable=False)
    min_price_sqft = Column(Float, nullable=False)
    max_price_sqft = Column(Float, nullable=False)

    # Метрики DOM (Days On Market)
    avg_dom = Column(Float, nullable=True)
    min_dom = Column(Integer, nullable=True)
    max_dom = Column(Integer, nullable=True)

    # Результаты анализа
    color = Column(String(20), nullable=False, index=True)  # green, light_green, yellow, red
    sample_size = Column(Integer, nullable=False)  # Количество домов в выборке
    confidence_score = Column(Float, nullable=False)  # 0.0 - 1.0

    last_updated = Column(DateTime, default=datetime.utcnow)

    # Уникальный индекс на комбинацию улица + город
    __table_args__ = (
        Index('idx_street_city_unique', 'street_name', 'city', unique=True),
    )


class LandOpportunity(Base):
    """
    Модель земельного участка
    Хранит информацию о землях из email, результаты анализа и фильтрации
    """
    __tablename__ = 'land_opportunities'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Источник данных
    email_id = Column(String(200), nullable=True)
    received_at = Column(DateTime, nullable=False)

    # Основные данные
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    price = Column(Float, nullable=False)
    lot_size = Column(Float, nullable=True)  # acres
    zoning = Column(String(50), nullable=True)
    mls_number = Column(String(50), nullable=True, index=True)
    url = Column(String(500), nullable=True)  # URL листинга

    # Утилиты (city_well, public_well, none)
    has_well = Column(String(20), nullable=True)
    has_septic = Column(String(20), nullable=True)  # city_septic, public_septic, none

    # Анализ зоны (откуда земля)
    zone_color = Column(String(20), nullable=True, index=True)
    nearby_avg_price_sqft = Column(Float, nullable=True)
    nearby_sales_count = Column(Integer, nullable=True)
    nearby_avg_dom = Column(Float, nullable=True)
    market_status = Column(String(20), nullable=True)  # cold, stable, growing, overheated

    # Результаты фильтрации
    filter_passed = Column(Boolean, nullable=False, index=True)
    filter_reasons = Column(Text, nullable=True)  # JSON строка с массивом причин

    # Оценка выгодности
    urgency_level = Column(String(20), nullable=True, index=True)  # urgent, good, normal
    urgency_score = Column(Integer, nullable=True)  # 0-100

    # Telegram уведомления
    telegram_sent = Column(Boolean, default=False)
    telegram_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class MarketHeatZone(Base):
    """
    Модель анализа перегрева рынка по ZIP коду
    Хранит метрики активности рынка и рекомендации
    """
    __tablename__ = 'market_heat_zones'

    id = Column(Integer, primary_key=True, autoincrement=True)
    zip_code = Column(String(10), unique=True, nullable=False, index=True)

    # Метрики рынка
    active_listings = Column(Integer, nullable=False)  # Активных листингов
    sold_last_90d = Column(Integer, nullable=False)    # Продано за 90 дней
    inventory_months = Column(Float, nullable=False)   # Месяцев инвентаря
    price_change_90d = Column(Float, nullable=True)    # Изменение цен (%)
    dom_change = Column(Float, nullable=True)          # Изменение DOM (%)

    # Результаты анализа
    status = Column(String(20), nullable=False)  # cold, stable, growing, overheated
    recommendation = Column(Text, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# СЛУЖЕБНЫЕ ФУНКЦИИ
# ============================================================================

def create_tables():
    """
    Создает все таблицы в базе данных если их нет
    Вызывается при первом запуске системы
    """
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """
    Возвращает новую сессию базы данных
    После работы с сессией нужно вызвать session.close()
    """
    return SessionLocal()


def drop_all_tables():
    """
    ОПАСНО! Удаляет все таблицы из базы данных
    Использовать только для разработки/тестирования
    """
    Base.metadata.drop_all(bind=engine)
