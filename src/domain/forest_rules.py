from enum import Enum
from typing import List, Dict, Optional, Tuple

class ScopeType(str, Enum):
    MITTEN = "mitten" # Конкретна рукавичка (найвищий пріоритет)
    ZONE = "zone" # Частина лісу (середній пріоритет)
    ALL_FOREST = "all_forest" # Весь ліс (базовий пріоритет)

# Точний список 8 рукавичок
MITTENS: List[str] = [
    "Під ялиною",
    "У соснах",
    "Біля мурашника",
    "Під дубом",
    "У ліщині",
    "Під вербою",
    "Біля бобрової греблі",
    "На узліссі",
]
# Точний список 3 зон лісу
ZONES: List[str] = [
    "хвойна частина",
    "листяна частина",
    "біля річки",
]
# Мапінг зон до рукавичок
ZONE_TO_MITTENS: Dict[str, List[str]] = {
    "хвойна частина": ["Під ялиною", "У соснах", "Біля мурашника"],
    "листяна частина": ["Під дубом", "У ліщині", "Під вербою"],
    "біля річки": ["Біля бобрової греблі", "Під вербою"],
}
# Мапінг кожної рукавички до зон (Під вербою входить у дві зони!)
MITTEN_TO_ZONES: Dict[str, List[str]] = {
    "Під ялиною": ["хвойна частина"],
    "У соснах": ["хвойна частина"],
    "Біля мурашника": ["хвойна частина"],
    "Під дубом": ["листяна частина"],
    "У ліщині": ["листяна частина"],
    "Під вербою": ["листяна частина", "біля річки"],
    "Біля бобрової греблі": ["біля річки"],
    "На узліссі": [],  # Не належить до жодної з трьох зон
}
def normalize_location_name(name: str) -> Optional[Tuple[ScopeType, str]]:
    """
    Нормалізує введену або знайдену назву локації.
    Повертає кортеж (ScopeType, канонічна_назва) або None, якщо не розпізнано.
    """
    cleaned = name.strip().lower()
    # 1. Перевірка на "весь ліс"
    if cleaned in ["весь ліс", "ліс", "загальний", "all", "all_forest", "для всього лісу"]:
        return (ScopeType.ALL_FOREST, "весь ліс")
    # 2. Прямий збіг із рукавичками
    for mitten in MITTENS:
        m_lower = mitten.lower()
        if m_lower == cleaned or m_lower in cleaned or cleaned in m_lower:
            return (ScopeType.MITTEN, mitten)
    # 3. Синоніми та форми слів для рукавичок
    synonyms_mitten = {
        "ялина": "Під ялиною",
        "ялини": "Під ялиною",
        "ялинами": "Під ялиною",
        "сосна": "У соснах",
        "сосни": "У соснах",
        "сосон": "У соснах",
        "соснами": "У соснах",
        "мурашник": "Біля мурашника",
        "мурашника": "Біля мурашника",
        "дуб": "Під дубом",
        "дубом": "Під дубом",
        "дуба": "Під дубом",
        "ліщина": "У ліщині",
        "ліщиною": "У ліщині",
        "ліщини": "У ліщині",
        "верба": "Під вербою",
        "вербою": "Під вербою",
        "верби": "Під вербою",
        "гребля": "Біля бобрової греблі",
        "бобри": "Біля бобрової греблі",
        "боброва гребля": "Біля бобрової греблі",
        "бобрової греблі": "Біля бобрової греблі",
        "узлісся": "На узліссі",
        "узліссі": "На узліссі",
    }
    for syn, canonical in synonyms_mitten.items():
        if syn in cleaned:
            return (ScopeType.MITTEN, canonical)
    # 4. Перевірка на зони лісу
    for zone in ZONES:
        if zone in cleaned:
            return (ScopeType.ZONE, zone)
    if "хвойн" in cleaned or "хвоя" in cleaned:
        return (ScopeType.ZONE, "хвойна частина")
    if "листян" in cleaned:
        return (ScopeType.ZONE, "листяна частина")
    if "річк" in cleaned or "водойм" in cleaned or "берег" in cleaned:
        return (ScopeType.ZONE, "біля річки")
    return None
def get_applicable_scopes_for_target(scope_type: ScopeType, target_name: str) -> List[Tuple[ScopeType, str, int]]:
    """
    Повертає список областей (scopes), які діють для цілі пошуку, 
    відсортований за спаданням специфічності (пріоритету).
    Кортеж: (scope_type, scope_name, priority_weight)
    
    Ієрархія вагів:
    - Рукавичка (MITTEN): 30
    - Зона (ZONE): 20
    - Весь ліс (ALL_FOREST): 10
    """
    results: List[Tuple[ScopeType, str, int]] = []
    if scope_type == ScopeType.MITTEN:
        # 1. Специфічне правило конкретної рукавички
        results.append((ScopeType.MITTEN, target_name, 30))
        # 2. Правила зон, куди вона входить
        for zone in MITTEN_TO_ZONES.get(target_name, []):
            results.append((ScopeType.ZONE, zone, 20))
        # 3. Загальні правила для всього лісу
        results.append((ScopeType.ALL_FOREST, "весь ліс", 10))
    elif scope_type == ScopeType.ZONE:
        # 1. Правила самої зони
        results.append((ScopeType.ZONE, target_name, 20))
        # 2. Загальні правила для всього лісу
        results.append((ScopeType.ALL_FOREST, "весь ліс", 10))
    elif scope_type == ScopeType.ALL_FOREST:
        # Тільки правила для всього лісу
        results.append((ScopeType.ALL_FOREST, "весь ліс", 10))
    return results