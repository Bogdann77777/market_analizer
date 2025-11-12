# Asheville Land Analyzer

Система анализа рынка недвижимости для поиска выгодных земельных участков в районе Asheville, NC.

## ✅ УСТАНОВКА ЗАВЕРШЕНА

### Что установлено:

1. **Виртуальное окружение**: `venv/`
2. **Все зависимости** установлены (SQLAlchemy, Pandas, NumPy, Folium, Geopy, Gmail API, Telegram Bot)
3. **Структура проекта** готова для работы с реальными данными

### Структура проекта:

```
E:\market_analyzer\
├── venv/                      # Виртуальное окружение
├── src/
│   ├── config.py              # Конфигурация
│   ├── data/
│   │   ├── database.py       # SQLAlchemy модели
│   │   ├── geocoder.py       # Геокодирование
│   │   └── mls_importer.py   # Импорт CSV
│   ├── analyzers/
│   │   ├── price_calculator.py
│   │   ├── street_analyzer.py
│   │   ├── market_heat.py
│   │   └── land_scorer.py
│   ├── gmail/
│   │   ├── gmail_client.py
│   │   ├── parser.py
│   │   └── filter.py
│   ├── map/
│   │   ├── generator.py
│   │   ├── layers.py
│   │   └── popups.py
│   ├── telegram/
│   │   └── bot.py
│   └── scripts/
│       ├── import_mls_data.py
│       ├── update_street_colors.py
│       └── check_email.py
├── credentials/              # Для Gmail credentials
├── data/                     # Для MLS CSV файлов
├── output/                   # Для сгенерированных карт
├── .env                      # Конфигурация (заполнить!)
└── requirements.txt          # Зависимости
```

## 🚀 Быстрый старт

### Windows - Один клик:

**Двойной клик на:**
```
START.bat
```

При первом запуске автоматически установит зависимости.
Затем откроет интерактивное меню.

---

### Linux/Mac - Ручной запуск:

**1. Активировать виртуальное окружение:**
```bash
source venv/bin/activate
```

**2. Настроить .env файл:**

Заполнить реальные значения в `.env`:
```env
DATABASE_URL=postgresql://username:password@host:port/database_name
TELEGRAM_BOT_TOKEN=your_real_bot_token
```

### 3. Создать таблицы БД:

```bash
python -c "from src.data.database import create_tables; create_tables(); print('Database ready!')"
```

## 📊 Основные команды

### Импорт MLS данных:

Положить реальный CSV файл в `data/` и импортировать:

```bash
python src/scripts/import_mls_data.py data/your_mls_data.csv --create-tables
```

### Анализ улиц и присвоение цветов:

```bash
python src/scripts/update_street_colors.py
```

### Генерация интерактивной карты:

```bash
python -c "from src.map.generator import generate_full_map; generate_full_map()"
```

### Проверка email (требует Gmail credentials):

```bash
python src/scripts/check_email.py --telegram-chat-id YOUR_CHAT_ID
```

### Запуск Telegram бота:

```bash
python src/telegram/bot.py
```

## ⚙️ Конфигурация

### Требуемые переменные в `.env`:

```env
# PostgreSQL (обязательно для production)
DATABASE_URL=postgresql://username:password@host:port/database_name

# Telegram Bot Token (получить от @BotFather)
TELEGRAM_BOT_TOKEN=your_real_bot_token
```

### Gmail API:
1. Скачать credentials с https://console.cloud.google.com/
2. Сохранить как `credentials/gmail_credentials.json`

## 📦 Установленные зависимости

- SQLAlchemy 2.0.44
- Pandas 2.3.3
- NumPy 2.3.4
- Geopy 2.4.1
- Folium 0.20.0
- Google Auth + Gmail API
- python-telegram-bot 22.5
- python-dotenv 1.2.1

## 📝 Рабочий процесс

1. Подготовить реальный MLS CSV файл
2. Настроить PostgreSQL и заполнить `.env`
3. Создать таблицы: `python -c "from src.data.database import create_tables; create_tables()"`
4. Импортировать данные: `python src/scripts/import_mls_data.py data/your_file.csv`
5. Анализ улиц: `python src/scripts/update_street_colors.py`
6. Генерация карты: `python -c "from src.map.generator import generate_full_map; generate_full_map()"`
7. Открыть `output/asheville_land_map.html`

## 🔐 Gmail API Setup

Для автоматической проверки email с земельными участками:

1. Создать проект на https://console.cloud.google.com/
2. Включить Gmail API
3. Скачать OAuth2 credentials
4. Сохранить как `credentials/gmail_credentials.json`
5. Запустить: `python src/scripts/check_email.py --telegram-chat-id YOUR_ID`

## 🤖 Telegram Bot Setup

Для получения уведомлений о новых участках:

1. Создать бота через @BotFather в Telegram
2. Скопировать токен в `.env`
3. Запустить: `python src/telegram/bot.py`
4. Команды: /start, /help, /top, /map

---

**Проект готов для работы с реальными данными**
