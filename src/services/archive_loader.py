import json
from pathlib import Path

from src.database.db import Database
from src.database.models import DocumentRecord
from src.services.parser import extract_text_from_file, is_supported_file
from src.services.groq_service import GroqService
from src.domain.forest_rules import normalize_location_name, ScopeType


async def load_initial_archive(archive_path: Path, db: Database, groq_service: GroqService) -> int:

    if await db.has_documents():
        return 0

    archive_path = Path(archive_path)
    if not archive_path.exists():
        return 0

    # Читаємо кеш для відсканованих PDF
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
        
        # 1. Визначаємо локацію
        loc_match = normalize_location_name(filename)
        if loc_match:
            scope_type, location = loc_match
        else:
            scope_type, location = ScopeType.ALL_FOREST, "весь ліс"

        # 2. Вилучаємо текст
        try:
            content = extract_text_from_file(file_path)
        except Exception:
            content = ""

        # Якщо це сканований PDF — беремо повний розпізнаний текст із кешу
        if not content.strip() and filename in ocr_data:
            content = ocr_data[filename]
        elif not content.strip():
            content = f"Лісовий документ «{filename}» для локації «{location}»."

        doc = DocumentRecord(
            filename=filename,
            filepath=str(file_path),
            scope_type=scope_type.value,
            location=location,
            content=content,
            author_name=None,      
            uploaded_at=None,
            is_active=True,
            version=1
        )
        await db.save_document(doc)
        count += 1

    return count
