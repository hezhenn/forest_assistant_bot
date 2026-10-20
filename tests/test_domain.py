import pytest
from src.domain.forest_rules import (
    MITTENS,
    ZONES,
    MITTEN_TO_ZONES,
    ZONE_TO_MITTENS,
    ScopeType,
    normalize_location_name,
    get_applicable_scopes_for_target,
)


def test_mitten_and_zone_counts():
    """Перевірка, що в лісі рівно 8 рукавичок і 3 зони."""
    assert len(MITTENS) == 8
    assert len(ZONES) == 3


def test_pid_verboyu_in_two_zones():
    """Перевірка бізнес-вимоги: рукавичка «Під вербою» належить одночасно до двох зон."""
    zones = MITTEN_TO_ZONES["Під вербою"]
    assert "листяна частина" in zones
    assert "біля річки" in zones
    assert len(zones) == 2


def test_na_uzlissi_is_autonomous():
    """Перевірка бізнес-вимоги: «На узліссі» не належить до жодної з трьох зон."""
    assert MITTEN_TO_ZONES["На узліссі"] == []


def test_normalize_location_exact_and_synonyms():
    """Перевірка розпізнавання відмінків та синонімів рукавичок."""
    assert normalize_location_name("під дубом") == (ScopeType.MITTEN, "Під дубом")
    assert normalize_location_name("дубом") == (ScopeType.MITTEN, "Під дубом")
    assert normalize_location_name("соснах") == (ScopeType.MITTEN, "У соснах")
    assert normalize_location_name("бобри") == (ScopeType.MITTEN, "Біля бобрової греблі")
    assert normalize_location_name("весь ліс") == (ScopeType.ALL_FOREST, "весь ліс")


def test_normalize_location_unicode_nfc():
    """Перевірка підтримки декомпонованого Unicode (NFD/NFC)."""
    # Буква 'ї' у слові 'греблі'
    assert normalize_location_name("Біля бобрової греблі") == (ScopeType.MITTEN, "Біля бобрової греблі")


def test_specificity_hierarchy_weights_for_mitten():
    """
    Перевірка ієрархії специфічності для конкретної рукавички:
    1. Рукавичка повинна мати вагу 30
    2. Зона лісу повинна мати вагу 20
    3. Весь ліс повинен мати вагу 10
    """
    scopes = get_applicable_scopes_for_target(ScopeType.MITTEN, "Під ялиною")
    
    # Має бути 3 рівні: сама рукавичка, хвойна частина, весь ліс
    assert len(scopes) == 3
    assert scopes[0] == (ScopeType.MITTEN, "Під ялиною", 30)
    assert scopes[1] == (ScopeType.ZONE, "хвойна частина", 20)
    assert scopes[2] == (ScopeType.ALL_FOREST, "весь ліс", 10)


def test_specificity_hierarchy_weights_for_zone():
    """Перевірка ієрархії для запиту про зону лісу."""
    scopes = get_applicable_scopes_for_target(ScopeType.ZONE, "листяна частина")
    assert len(scopes) == 2
    assert scopes[0] == (ScopeType.ZONE, "листяна частина", 20)
    assert scopes[1] == (ScopeType.ALL_FOREST, "весь ліс", 10)


def test_specificity_hierarchy_weights_for_all_forest():
    """Перевірка ієрархії для загальнолісового запиту."""
    scopes = get_applicable_scopes_for_target(ScopeType.ALL_FOREST, "весь ліс")
    assert len(scopes) == 1
    assert scopes[0] == (ScopeType.ALL_FOREST, "весь ліс", 10)
