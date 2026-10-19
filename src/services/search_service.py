from typing import List, Tuple
from rank_bm25 import BM25Okapi

from src.database.db import Database
from src.database.models import DocumentRecord
from src.domain.forest_rules import (
    ScopeType, get_applicable_scopes_for_target
)


def tokenize(text: str) -> List[str]:
    import re
    return re.findall(r"\w+", text.lower())


class SearchService:
    def __init__(self, db: Database):
        self.db = db

    async def search_relevant_documents(
        self,
        query: str,
        target_scope_type: ScopeType,
        target_name: str,
        top_k: int = 4
    ) -> List[DocumentRecord]:
        # 1. Отримуємо всі діючі рівні для цієї локації
        applicable_scopes = get_applicable_scopes_for_target(target_scope_type, target_name)
        locations_to_query = [scope[1] for scope in applicable_scopes]
        weight_map = {scope[1]: scope[2] for scope in applicable_scopes}

        # 2. Отримуємо активні документи з бази
        docs = await self.db.get_active_documents(locations_to_query)
        if not docs:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return sorted(docs, key=lambda d: weight_map.get(d.location, 0), reverse=True)[:top_k]

        # 3. Рахуємо текстову відповідність через BM25
        corpus = [tokenize(f"{d.filename} {d.content}") for d in docs]
        bm25 = BM25Okapi(corpus)
        bm25_scores = bm25.get_scores(query_tokens)

        # 4. Обчислюємо фінальний скор
        # Вага специфічності (30, 20, 10) помножується на 10, щоб конкретна рукавичка
        # завжди стояла вище за загальну лісову пораду, навіть якщо в загальній більше спільних слів.
        scored_docs: List[Tuple[float, DocumentRecord]] = []
        for doc, bm_score in zip(docs, bm25_scores):
            specificity_weight = weight_map.get(doc.location, 10)
            total_score = (specificity_weight * 10.0) + float(bm_score)
            scored_docs.append((total_score, doc))

        # Сортуємо від найбільшого балу до найменшого
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        return [doc for score, doc in scored_docs[:top_k]]
