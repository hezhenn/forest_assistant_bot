import html
import re

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from src.services.groq_service import GroqService
from src.services.search_service import SearchService
from src.bot.keyboards import get_locations_keyboard
from src.domain.forest_rules import ScopeType

def format_to_html(text: str) -> str:
    safe = html.escape(text)
    safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
    safe = re.sub(r'(?m)^[\*\-]\s+', '• ', safe)
    return safe

router = Router(name="questions_router")


@router.message(F.text, ~F.text.startswith("/"))
async def handle_user_question(
    message: Message,
    state: FSMContext,
    groq_service: GroqService,
    search_service: SearchService
) -> None:
    # Перевіряємо, чи користувач не перебуває у спеціальному стані завантаження файлу
    current_state = await state.get_state()
    if current_state is not None:
        return

    query = message.text.strip()
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # 1. Визначаємо локацію з тексту запитання
    detected = await groq_service.detect_query_location(query)

    if not detected:
        await state.update_data(saved_query=query)
        await message.answer(
            "🦊 Підкажи, будь ласка, для якої з 8 рукавичок чи частини лісу ти шукаєш пораду?",
            reply_markup=get_locations_keyboard()
        )
        return

    scope_type, location = detected

    # 2. Шукаємо релевантні документи за ієрархією специфічності
    docs = await search_service.search_relevant_documents(
        query=query,
        target_scope_type=scope_type,
        target_name=location
    )

    # 3. Генеруємо відповідь через Groq
    answer = await groq_service.generate_answer(
        query=query,
        target_location=location,
        documents=docs
    )

    await message.answer(format_to_html(answer))


@router.callback_query(F.data.startswith("loc:"))
async def handle_location_choice_for_query(
    callback: CallbackQuery,
    state: FSMContext,
    groq_service: GroqService,
    search_service: SearchService
) -> None:

    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer()
        return

    scope_type_str = parts[1]
    location = parts[2]
    scope_type = ScopeType(scope_type_str)

    data = await state.get_data()
    saved_query = data.get("saved_query", "")
    await state.clear()

    await callback.answer(f"Обрано: {location}")
    await callback.message.edit_text(f"🔍 Шукаю пораду для: <b>{html.escape(location)}</b>...")
    await callback.message.bot.send_chat_action(chat_id=callback.message.chat.id, action="typing")

    # Шукаємо документи для обраної локації
    docs = await search_service.search_relevant_documents(
        query=saved_query,
        target_scope_type=scope_type,
        target_name=location
    )

    answer = await groq_service.generate_answer(
        query=saved_query,
        target_location=location,
        documents=docs
    )

    await callback.message.edit_text(format_to_html(answer))
