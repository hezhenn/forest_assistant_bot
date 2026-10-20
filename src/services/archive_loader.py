import json
import unicodedata
from pathlib import Path

from src.database.db import Database
from src.database.models import DocumentRecord
from src.services.parser import extract_text_from_file, is_supported_file
from src.services.groq_service import GroqService
from src.domain.forest_rules import normalize_location_name, ScopeType, MITTENS


def detect_archive_scope(filename: str, content: str):

    clean_fn = unicodedata.normalize("NFC", filename).lower()
    clean_cnt = unicodedata.normalize("NFC", content[:600]).lower()

    # 1. Спроба розпізнати локацію з назви файлу
    loc_match = normalize_location_name(clean_fn)
    if loc_match:
        return loc_match[0], loc_match[1], True

    # 2. Якщо в назві немає — шукаємо чіткі вказівки на початку тексту
    for mitten in MITTENS:
        m_low = mitten.lower()
        if m_low in clean_cnt or f"рукавичці {m_low}" in clean_cnt:
            return ScopeType.MITTEN, mitten, True

    if "хвойного лісу" in clean_cnt or "хвойній частині" in clean_cnt:
        return ScopeType.ZONE, "хвойна частина", True
    if "листяного лісу" in clean_cnt or "листяній частині" in clean_cnt:
        return ScopeType.ZONE, "листяна частина", True
    if "біля річки" in clean_cnt or "мешканців біля річки" in clean_cnt:
        return ScopeType.ZONE, "біля річки", True

    if "для всіх мешканців лісу" in clean_cnt or "всіх мешканців лісу" in clean_cnt or "для всього лісу" in clean_cnt:
        return ScopeType.ALL_FOREST, "весь ліс", True

    # 3. Призначення незрозуміле -> КАРАНТИН (правило Мишки)
    return ScopeType.ALL_FOREST, "невизначено", False


async def load_initial_archive(archive_path: Path, db: Database, groq_service: GroqService) -> int:
    if await db.has_documents():
        return 0

    archive_path = Path(archive_path)
    if not archive_path.exists():
        return 0

    ocr_cache_path = Path(__file__).parent / "ocr_cache.json"
    ocr_data = {}
    if ocr_cache_path.exists():
        try:
            with open(ocr_cache_path, "r", encoding="utf-8") as f:
                ocr_data = json.load(f)
        except Exception:
            ocr_data = {}

    count = 0
    files = [f for f in archive_path.iterdir() if f.is_file() and is_supported_file(f.name)]

    for file_path in files:
        filename = file_path.name

        # Вилучаємо текст
        try:
            content = extract_text_from_file(file_path)
        except Exception:
            content = ""

        # Якщо це сканований PDF — беремо повний розпізнаний текст із кешу
        if not content.strip() and filename in ocr_data:
            content = ocr_data[filename]
        elif not content.strip():
            content = f"Лісовий документ «{filename}»."

        # Визначаємо локацію та активність за правилом Мишки
        scope_type, location, is_active = detect_archive_scope(filename, content)

        doc = DocumentRecord(
            filename=filename,
            filepath=str(file_path),
            scope_type=scope_type.value,
            location=location,
            content=content,
            author_name=None,
            uploaded_at=None,
            is_active=is_active,
            version=1
        )
        await db.save_document(doc)
        count += 1

    return count
