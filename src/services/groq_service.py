from os import system
import json 
from typing import Optional, Tuple, List
from groq import AsyncGroq

from src.config import settings
from src.domain.forest_rules import (
    MITTENS, ZONES, ScopeType, normalize_location_name
)
from src.database.models import DocumentRecord

class GroqService:
    def __init__(self):
        self.client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    async def detect_query_location(self, query: str) -> Optional[Tuple[ScopeType, str]]:
        # Швидка перевірка за доменними правилами
        direct_match = normalize_location_name(query)
        if direct_match:
            return direct_match
        
        system_prompt = f"""Ти аналітик лісової бази знань. У нас є 8 рукавичок:
            {', '.join(MITTENS)}.
            Також є зони лісу: {', '.join(ZONES)}.
            І рівень 'весь ліс'.
            Твоє завдання: визначити, про яку саме локацію запитує звір.
            Відповідай ВИКЛЮЧНО валідним JSON-об'єктом без зайвого тексту:
            {{
                "found": true,
                "location": "Назва рукавички / зони / весь ліс",
                "scope_type": "mitten"
            }}
            Якщо локація в питанні взагалі не згадується — повертай {{"found": false}}."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Питання звіра: {query}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            if data.get("found") and data.get("location"):
                norm = normalize_location_name(data["location"])
                if norm:
                    return norm
        except Exception:
            pass

        return None

    async def analyze_document_location(self, filename: str, content: str) -> Tuple[Optional[ScopeType], Optional[str], bool]:
        """
        Аналізує текст нового документа, щоб зрозуміти його область дії.
        Повертає: (ScopeType, назва_локації, is_ambiguous).
        Якщо призначення незрозуміле (наприклад «біля нашої рукавички») — is_ambiguous=True.
        """
        snippet = content[:2500]
        system_prompt = f"""Ти експерт з аналізу лісових порад.
            У нашому лісі діє 8 рукавичок-ОСББ: {', '.join(MITTENS)}.
            Зони лісу: {', '.join(ZONES)}.
            Також документи можуть бути для всього лісу ('весь ліс').
            ВАЖЛИВЕ ПРАВИЛО ВІД ЗАМОВНИКА:
            Якщо з тексту неможливо ТОЧНО зрозуміти, для якої це рукавички чи частини лісу 
            (наприклад, сказано просто «біля нашої рукавички», «наше подвір'я» або взагалі немає прив'язки),
            ти КАТЕГОРИЧНО НЕ ПОВИНЕН ВГАДУВАТИ. У такому разі вкажи "ambiguous": true.
            Відповідай ВИКЛЮЧНО у форматі JSON:
            {{
            "ambiguous": false,
            "scope_type": "mitten",
            "location": "Точна назва однієї з 8 рукавичок / зони / весь ліс"
            }}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Назва файлу: {filename}\n\nТекст документа:\n\n{snippet}"}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            
            if data.get("ambiguous"):
                return None, None, True
            
            loc_raw = data.get("location")
            if loc_raw:
                norm = normalize_location_name(loc_raw)
                if norm:
                    return norm[0], norm[1], False
            
            return None, None, False
        except Exception:
            return None, None, False

    async def generate_answer(
        self,
        query: str,
        target_location: str,
        documents: List[DocumentRecord]
    ) -> str:
        """
        Генерує відповідь на питання звіра, опираючись ТІЛЬКИ на знайдені документи.
        Виконує обов'язкові вимоги:
        1. Вказувати джерело (назву документа).
        2. Якщо документ надіслав звір — називати його справжнє ім'я та дату надсилання.
        3. Якщо інформації немає — чесно сказати про це без вигадок.
        """
        if not documents:
            return (
                f"У лісовому архіві для локації «{target_location}» поки що немає порад на цю тему. "
                f"Можливо, ти захочеш поділитися своєю порадою, щоб поповнити архів?"
            )
            
        context_parts = []
        for i, doc in enumerate(documents, 1):
            if doc.author_name and doc.uploaded_at:
                author_info = f" (Автор: {doc.author_name}, надіслано: {doc.uploaded_at})"
            elif doc.author_name:
                author_info = f" (Автор: {doc.author_name})"
            else:
                author_info = f" (Джерело: Лісовий архів)"

            context_parts.append(
                f"--- Документ #{i}: «{doc.filename}»{author_info} | Локація: {doc.location} ---\n{doc.content[:3000]}\n"
            )
        context_text = "\n".join(context_parts)
        system_prompt = f"""Ти — помічник «Мишка-шкряботушка» у лісовому Telegram-боті.
            Звірі звертаються до тебе за порадами. Твоє завдання:
            1. Відповідати українською мовою — просто, доброзичливо й коротко по суті.
            2. ВІДПОВІДАТИ ТІЛЬКИ НА ОСНОВІ НАДАНИХ ДОКУМЕНТІВ. Категорично заборонено вигадувати те, чого немає в тексті!
            3. ОБОВ'ЯЗКОВО вказувати у відповіді назву документа, з якого взято пораду.
            4. Якщо документ надіслав звір (є автор і дата) — ОБОВ'ЯЗКОВО назвати його справжнє ім'я та дату надсилання.
            5. Якщо в наданих документах НЕМАЄ відповіді на запитання — ввічливо скажи, що в документах для цієї локації немає потрібної інформації, і запропонуй надіслати свою пораду."""
        user_prompt = f"""Локація, про яку питає звір: «{target_location}»
            Запитання звіра: {query}
            Доступні документи з порадами:
            {context_text}
            Дай ввічливу та точну відповідь з обов'язковою атрибуцією джерела."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
            