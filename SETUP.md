# Первый запуск проекта

## ⚠️ ВАЖНО: Проект требует реальные данные

Все заглушки удалены. Проект не запустится без реальной конфигурации.

## 1. Настроить PostgreSQL

Создать базу данных:
```sql
CREATE DATABASE asheville_land;
```

## 2. Заполнить .env

Открыть `.env` и заполнить реальные значения:

```env
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/asheville_land
TELEGRAM_BOT_TOKEN=your_real_bot_token_from_botfather
```

## 3. Активировать venv

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

## 4. Создать таблицы

```bash
python -c "from src.data.database import create_tables; create_tables(); print('Database ready!')"
```

## 5. Подготовить MLS данные

Положить реальный CSV файл в `data/`:
- `data/your_mls_export.csv`

Требуемые колонки:
- Address, City, State, Zip
- SalePrice или ListPrice
- Sqft (площадь дома)
- LotSize (размер участка в акрах)
- Status (active/sold)
- ListDate, SaleDate
- MLSNumber
- Bedrooms, Bathrooms (опционально)

## 6. Импорт данных

```bash
python src/scripts/import_mls_data.py data/your_mls_export.csv
```

## 7. Анализ

```bash
python src/scripts/update_street_colors.py
```

## 8. Генерация карты

```bash
python -c "from src.map.generator import generate_full_map; generate_full_map()"
```

Открыть: `output/asheville_land_map.html`

---

**Проект готов только для реальных данных. Никаких заглушек.**
