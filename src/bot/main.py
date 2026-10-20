import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.config import settings
from src.database.db import Database
from src.services.groq_service import GroqService
from src.services.search_service import SearchService
from src.services.archive_loader import load_initial_archive

from src.bot.handlers import base, uploads, questions


async def main() -> None:
    # Налаштування логування
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout
    )
    logger = logging.getLogger("forest_bot")
    logger.info("🌲 Ініціалізація Лісового порадника...")

    # 1. Ініціалізуємо базу даних
    db = Database(settings.db_path)
    await db.init_db()
    logger.info("✅ База даних SQLite успішно ініціалізована.")

    groq_service = GroqService()
    search_service = SearchService(db=db)

    # 2. Автоматичне завантаження початкового архіву на старті
    loaded_count = await load_initial_archive(
        archive_path=settings.forest_archive_path,
        db=db,
        groq_service=groq_service
    )
    if loaded_count > 0:
        logger.info(f"📚 Завантажено {loaded_count} документів з теки «Лісовий архів».")
    else:
        logger.info("📚 Початковий архів уже був завантажений раніше.")

    # 3. Ініціалізація бота та диспетчера
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 4. Реєструємо роутери
    dp.include_router(base.router)
    dp.include_router(uploads.router)
    dp.include_router(questions.router)

    logger.info("🚀 Бот «Мишка-шкряботушка» успішно запущений і слухає Telegram!")

    # 5. Запуск polling з передачею сервісів у хендлери
    await dp.start_polling(
        bot,
        db=db,
        groq_service=groq_service,
        search_service=search_service
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот зупинений.")
