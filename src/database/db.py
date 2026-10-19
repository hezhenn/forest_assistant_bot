from pathlib import Path
from typing import Optional, List
import aiosqlite
from datetime import datetime

from src.database.models import DocumentRecord


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    async def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            # Таблиця авторів (звірів)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    real_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Таблиця документів
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    location TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author_name TEXT,
                    uploaded_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    version INTEGER DEFAULT 1
                )
            """)

            # Індекси для швидкого пошуку
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_location ON documents(location, is_active)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_scope ON documents(scope_type, is_active)
            """)
            await db.commit()

    # Робота з користувачами (звірами)

    async def get_user_real_name(self, telegram_id: int) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT real_name FROM users WHERE telegram_id = ?",
                (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def save_user(self, telegram_id: int, real_name: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (telegram_id, real_name, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET real_name = excluded.real_name
            """, (telegram_id, real_name.strip(), now))
            await db.commit()

    # Робота з документами

    async def save_document(self, doc: DocumentRecord) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO documents (
                    filename, filepath, scope_type, location, content,
                    author_name, uploaded_at, is_active, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.filename,
                doc.filepath,
                doc.scope_type,
                doc.location,
                doc.content,
                doc.author_name,
                doc.uploaded_at,
                1 if doc.is_active else 0,
                doc.version
            ))
            await db.commit()
            return cursor.lastrowid

    async def supersede_document(self, location: str, filename: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE documents
                SET is_active = 0
                WHERE location = ? AND filename = ? AND is_active = 1
            """, (location, filename))
            await db.commit()

    async def get_active_documents(self, locations: List[str]) -> List[DocumentRecord]:
        if not locations:
            return []

        placeholders = ",".join("?" for _ in locations)
        query = f"""
            SELECT id, filename, filepath, scope_type, location, content,
                   author_name, uploaded_at, is_active, version
            FROM documents
            WHERE is_active = 1 AND location IN ({placeholders})
            ORDER BY location, filename
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, locations) as cursor:
                rows = await cursor.fetchall()
                return [
                    DocumentRecord(
                        id=row["id"],
                        filename=row["filename"],
                        filepath=row["filepath"],
                        scope_type=row["scope_type"],
                        location=row["location"],
                        content=row["content"],
                        author_name=row["author_name"],
                        uploaded_at=row["uploaded_at"],
                        is_active=bool(row["is_active"]),
                        version=row["version"]
                    )
                    for row in rows
                ]

    async def get_all_active_documents(self) -> List[DocumentRecord]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT id, filename, filepath, scope_type, location, content,
                       author_name, uploaded_at, is_active, version
                FROM documents
                WHERE is_active = 1
            """) as cursor:
                rows = await cursor.fetchall()
                return [
                    DocumentRecord(
                        id=row["id"],
                        filename=row["filename"],
                        filepath=row["filepath"],
                        scope_type=row["scope_type"],
                        location=row["location"],
                        content=row["content"],
                        author_name=row["author_name"],
                        uploaded_at=row["uploaded_at"],
                        is_active=bool(row["is_active"]),
                        version=row["version"]
                    )
                    for row in rows
                ]

    async def has_documents(self) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM documents") as cursor:
                row = await cursor.fetchone()
                return (row[0] > 0) if row else False
