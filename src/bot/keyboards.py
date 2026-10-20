from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.domain.forest_rules import MITTENS, ZONES


def get_locations_keyboard() -> InlineKeyboardMarkup:

    buttons = []
    
    # 8 рукавичок (по 2 в ряд)
    row = []
    for m in MITTENS:
        row.append(InlineKeyboardButton(text=f"🧤 {m}", callback_data=f"loc:mitten:{m}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # 3 зони
    zone_row = [
        InlineKeyboardButton(text=f"🌲 {z}", callback_data=f"loc:zone:{z}")
        for z in ZONES
    ]
    buttons.append(zone_row[:2])
    buttons.append(zone_row[2:])

    # Весь ліс
    buttons.append([
        InlineKeyboardButton(text="🌳 Для всього лісу", callback_data="loc:all_forest:весь ліс")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_version_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Це оновлена версія", callback_data="ver:update"),
            InlineKeyboardButton(text="📄 Це нова окрема порада", callback_data="ver:new")
        ]
    ])
