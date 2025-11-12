"""
Модуль Telegram бота
Отправляет уведомления о новых земельных участках, обрабатывает команды
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import sys
import os

# Добавляем родительскую директорию в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TELEGRAM_BOT_TOKEN
from data.database import Property, LandOpportunity, get_session
from analyzers.price_calculator import format_currency


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /start

    Args:
        update: Telegram Update объект
        context: Telegram Context объект
    """
    welcome_message = """
🏞️ Добро пожаловать в Asheville Land Analyzer Bot!

Я помогу вам находить лучшие земельные участки для инвестиций в районе Asheville, NC.

Доступные команды:
/start - Начать работу с ботом
/help - Показать справку
/top - Показать топ-5 срочных земельных участков
/map - Получить ссылку на интерактивную карту

Вы будете получать автоматические уведомления о новых возможностях!
    """

    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /help

    Args:
        update: Telegram Update объект
        context: Telegram Context объект
    """
    help_message = """
📚 СПРАВКА ПО КОМАНДАМ:

/start - Начать работу с ботом
/help - Показать эту справку
/top - Топ-5 срочных земельных участков (score ≥ 80)
/map - Получить ссылку на интерактивную карту

🔔 Автоматические уведомления:
Вы получите уведомление когда:
- Найден участок с urgency score ≥ 80 (URGENT)
- Участок в зеленой зоне ($350+/sqft)
- Рынок растет (growing status)

💡 О системе скоринга:
- 80-100: 🔥 URGENT - немедленная покупка
- 50-79: ⭐ GOOD - хорошая возможность
- 0-49: ✅ Normal - рассмотреть позже
    """

    await update.message.reply_text(help_message)


async def top_lands_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /top - показывает топ-5 участков

    Args:
        update: Telegram Update объект
        context: Telegram Context объект
    """
    session = get_session()
    try:
        # Получить топ-5 по urgency_score
        top_opportunities = session.query(LandOpportunity).order_by(
            LandOpportunity.urgency_score.desc()
        ).limit(5).all()

        if not top_opportunities:
            await update.message.reply_text("Пока нет земельных участков в базе данных.")
            return

        # Сформировать сообщение
        message = "🔥 ТОП-5 ЗЕМЕЛЬНЫХ УЧАСТКОВ:\n\n"

        for idx, opp in enumerate(top_opportunities, 1):
            # Получить связанный Property
            prop = session.query(Property).filter_by(id=opp.property_id).first()

            if not prop:
                continue

            # Форматировать цену
            price = prop.list_price or prop.sale_price
            price_str = format_currency(price) if price else 'N/A'

            # Emoji для urgency
            if opp.urgency_level == 'urgent':
                emoji = '🔥'
            elif opp.urgency_level == 'good':
                emoji = '⭐'
            else:
                emoji = '✅'

            # Добавить в сообщение
            message += f"{idx}. {emoji} Score: {opp.urgency_score}/100\n"
            message += f"   📍 {prop.address}, {prop.city}\n"
            message += f"   💰 {price_str}"

            if prop.lot_size:
                message += f" | 📐 {prop.lot_size:.2f} acres"

            message += f"\n   🟢 {opp.zone_color} zone | 📊 {opp.market_status}\n\n"

        await update.message.reply_text(message)

    finally:
        session.close()


async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает команду /map - отправляет ссылку на карту

    Args:
        update: Telegram Update объект
        context: Telegram Context объект
    """
    message = """
🗺️ ИНТЕРАКТИВНАЯ КАРТА:

Карта доступна в файле: output/asheville_land_map.html

Для доступа к карте:
1. Запустите скрипт генерации карты
2. Откройте файл в браузере
3. Все участки будут показаны с цветовой кодировкой

🟢 Зеленые зоны - лучшие для инвестиций ($350+/sqft)
🟡 Желтые зоны - средние ($220-300/sqft)
🔴 Красные зоны - избегать (<$220/sqft)
    """

    await update.message.reply_text(message)


async def send_alert(application: Application, chat_id: int, land_opp: LandOpportunity) -> bool:
    """
    Отправляет уведомление о новом земельном участке

    Args:
        application: Telegram Application объект
        chat_id: ID чата для отправки
        land_opp: LandOpportunity объект

    Returns:
        True если успешно отправлено, False если ошибка
    """
    session = get_session()
    try:
        # Получить связанный Property
        prop = session.query(Property).filter_by(id=land_opp.property_id).first()

        if not prop:
            return False

        # Форматировать цену
        price = prop.list_price or prop.sale_price
        price_str = format_currency(price) if price else 'N/A'

        # Emoji для urgency
        if land_opp.urgency_level == 'urgent':
            emoji = '🔥 СРОЧНО!'
            title = 'НОВЫЙ СРОЧНЫЙ УЧАСТОК'
        elif land_opp.urgency_level == 'good':
            emoji = '⭐'
            title = 'НОВАЯ ХОРОШАЯ ВОЗМОЖНОСТЬ'
        else:
            emoji = '✅'
            title = 'НОВЫЙ УЧАСТОК'

        # Сформировать сообщение
        message = f"{emoji} {title}\n\n"
        message += f"📊 Urgency Score: {land_opp.urgency_score}/100\n\n"
        message += f"📍 Адрес: {prop.address}\n"
        message += f"🏙️ Город: {prop.city}, {prop.state} {prop.zip}\n\n"
        message += f"💰 Цена: {price_str}\n"

        if prop.lot_size:
            message += f"📐 Размер: {prop.lot_size:.2f} acres\n"
            # Рассчитать цену за акр
            if price:
                price_per_acre = price / prop.lot_size
                message += f"💵 Цена за акр: ${price_per_acre:,.0f}\n"

        # Добавить MLS номер
        if prop.mls_number:
            message += f"🏠 MLS: {prop.mls_number}\n"

        # Добавить URL листинга
        if prop.url:
            message += f"🔗 Ссылка: {prop.url}\n"

        message += f"\n🟢 Зона: {land_opp.zone_color.replace('_', ' ').title()}\n"
        message += f"📈 Рынок: {land_opp.market_status.title()}\n"
        message += f"🏘️ Средняя цена района: ${land_opp.nearby_avg_price_sqft:.2f}/sqft\n"
        message += f"📊 Продаж за 90 дней: {land_opp.recent_sales_count}\n\n"
        message += f"💡 {land_opp.notes}"

        # Отправить сообщение
        await application.bot.send_message(chat_id=chat_id, text=message)

        return True

    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")
        return False

    finally:
        session.close()


def run_bot() -> None:
    """
    Главная функция запуска Telegram бота
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен в .env файле")
        return

    print("🤖 Запускаю Telegram бота...")

    # Создать приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Зарегистрировать обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("top", top_lands_command))
    application.add_handler(CommandHandler("map", map_command))

    print("✅ Бот готов к работе!")
    print("   /start - начать")
    print("   /help - справка")
    print("   /top - топ участков")
    print("   /map - ссылка на карту")

    # Запустить polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    run_bot()
