from datetime import datetime
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.config import settings
from src.database.db import Database
from src.database.models import DocumentRecord
from src.services.parser import is_supported_file, extract_text_from_file
from src.services.groq_service import GroqService
from src.bot.states import DocumentUploadState
from src.bot.keyboards import get_locations_keyboard
from src.domain.forest_rules import ScopeType

router = Router(name="uploads_router")


@router.message(F.document)
async def handle_document_upload(
    message: Message,
    state: FSMContext,
    db: Database,
    groq_service: GroqService
) -> None:

    doc = message.document
    filename = doc.file_name or "документ"

    # 1. Перевіряємо формат
    if not is_supported_file(filename):
        await message.answer(
            f"❌ Формат файлу «{filename}» не підтримується.\n"
            "Лісовий архів приймає лише **PDF**, **Word (.docx)** або **TXT**."
        )
        return

    # 2. Завантажуємо файл на диск
    upload_dir = settings.db_path.parent / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{message.from_user.id}_{filename}"

    file_info = await message.bot.get_file(doc.file_id)
    await message.bot.download_file(file_info.file_path, destination=file_path)

    # 3. Вилучаємо текст
    try:
        content = extract_text_from_file(file_path)
    except Exception as e:
        await message.answer(f"Помилка при читанні файлу: {e}")
        return

    # 4. Перевіряємо, чи знаємо справжнє ім'я автора (вимога Мишки)
    author_name = await db.get_user_real_name(message.from_user.id)
    if not author_name:
        await state.update_data(
            pending_filename=filename,
            pending_filepath=str(file_path),
            pending_content=content
        )
        await state.set_state(DocumentUploadState.waiting_for_real_name)
        await message.answer(
            "👋 Привіт! Бачу, ти надсилаєш пораду до архіву вперше.\n"
            "Як твоє **справжнє ім'я**, звірятко? (наприклад: *Їжачок Тимко*, *Білочка Руда* або *Ведмідь*):",
            parse_mode="Markdown"
        )
        return

    # 5. Якщо ім'я вже є — переходимо до аналізу локації документа
    await process_document_saving(message, state, db, groq_service, filename, str(file_path), content, author_name)


@router.message(DocumentUploadState.waiting_for_real_name)
async def handle_author_real_name(
    message: Message,
    state: FSMContext,
    db: Database,
    groq_service: GroqService
) -> None:

    real_name = message.text.strip()
    if len(real_name) < 2:
        await message.answer("Будь ласка, напиши своє справжнє ім'я (хоча б 2 літери):")
        return

    # Зберігаємо ім'я назавжди за telegram_id
    await db.save_user(message.from_user.id, real_name)
    await message.answer(f"Приємно познайомитись, **{real_name}**! Запам'ятала тебе.", parse_mode="Markdown")

    data = await state.get_data()
    filename = data["pending_filename"]
    filepath = data["pending_filepath"]
    content = data["pending_content"]

    await process_document_saving(message, state, db, groq_service, filename, filepath, content, real_name)


async def process_document_saving(
    message: Message,
    state: FSMContext,
    db: Database,
    groq_service: GroqService,
    filename: str,
    filepath: str,
    content: str,
    author_name: str
) -> None:
    
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    scope_type, location, is_ambiguous = await groq_service.analyze_document_location(filename, content)

    if is_ambiguous or not location or not scope_type:
        await state.update_data(
            pending_filename=filename,
            pending_filepath=filepath,
            pending_content=content,
            pending_author=author_name
        )
        await state.set_state(DocumentUploadState.waiting_for_location)
        await message.answer(
            f"📄 Отримала твій документ «{filename}»!\n\n"
            "З тексту не зовсім зрозуміло, для якої саме рукавички чи частини лісу ця порада.\n"
            "Будь ласка, **обери локацію зі списку нижче** (не хочу вгадувати):",
            reply_markup=get_locations_keyboard()
        )
        return

    await finalize_document_save(message, state, db, filename, filepath, content, author_name, scope_type.value, location)


@router.callback_query(DocumentUploadState.waiting_for_location, F.data.startswith("loc:"))
async def handle_location_disambiguation(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database
) -> None:
    
    parts = callback.data.split(":")
    scope_type = parts[1]
    location = parts[2]

    data = await state.get_data()
    filename = data["pending_filename"]
    filepath = data["pending_filepath"]
    content = data["pending_content"]
    author_name = data["pending_author"]

    await callback.answer(f"Локацію обрано: {location}")
    await callback.message.edit_reply_markup(reply_markup=None)

    await finalize_document_save(
        callback.message, state, db, filename, filepath, content, author_name, scope_type, location
    )


async def finalize_document_save(
    message: Message,
    state: FSMContext,
    db: Database,
    filename: str,
    filepath: str,
    content: str,
    author_name: str,
    scope_type: str,
    location: str
) -> None:

    await db.supersede_document(location, filename)

    now_str = datetime.now().strftime("%d.%m.%Y")
    doc_record = DocumentRecord(
        filename=filename,
        filepath=filepath,
        scope_type=scope_type,
        location=location,
        content=content,
        author_name=author_name,
        uploaded_at=now_str,
        is_active=True,
        version=1
    )
    await db.save_document(doc_record)
    await state.clear()

    await message.answer(
        f"✅ **Пораду успішно додано до Лісового архіву!**\n\n"
        f"📄 Документ: «{filename}»\n"
        f"📍 Локація: **{location}**\n"
        f"✍️ Автор: **{author_name}**\n"
        f"📅 Дата: **{now_str}**\n\n"
        "Тепер інші звірі зможуть знаходити твою пораду у відповідях бота! 🐭❤️",
        parse_mode="Markdown"
    )
