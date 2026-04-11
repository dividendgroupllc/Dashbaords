from __future__ import annotations

import frappe


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
    {"label": "ГЛАВНЫЙ", "route": "/app/page-dashboard"},
    {"label": "ГЛАВНЫЙ", "route": "/app/kpi-dashboard"},
    {"label": "ОБОРОТ", "route": "/app/overview-dashboard"},
    {"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
    {"label": "КАССА", "route": "/app/cash-dashboard", "active": 1},
    {"label": "КЛИЕНТ", "route": "/app/client-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
]

MONTHS = [
    {"key": "january", "label": "January"},
    {"key": "february", "label": "February"},
    {"key": "march", "label": "March"},
    {"key": "april", "label": "April"},
    {"key": "may", "label": "May"},
    {"key": "june", "label": "June"},
    {"key": "july", "label": "July"},
    {"key": "august", "label": "August"},
    {"key": "september", "label": "September"},
    {"key": "october", "label": "October"},
    {"key": "november", "label": "November"},
    {"key": "december", "label": "December"},
]

CASH_ROWS = [
    {"label": "Бонус", "inflow": 0, "outflow": 14335000, "level": 0, "group": True},
    {"label": "Клиент", "inflow": 0, "outflow": 14335000, "level": 1},
    {"label": "Инвестор", "inflow": 0, "outflow": 573911050, "level": 0, "group": True},
    {"label": "пр.во", "inflow": 0, "outflow": 456079151, "level": 0, "group": True},
    {"label": "Продажа", "inflow": 3296487978, "outflow": 0, "level": 0, "group": True},
    {"label": "раохпер", "inflow": 0, "outflow": 41318091, "level": 0, "group": True},
    {"label": "сырьё", "inflow": 0, "outflow": 2225480786, "level": 0, "group": True},
]

BANK_ROWS = [
    {"label": "Инвестор", "inflow": 0, "outflow": 1006000, "level": 0, "group": True},
    {"label": "Инвестор1", "inflow": 0, "outflow": 1006000, "level": 1},
    {"label": "пр.во", "inflow": 0, "outflow": 31814733, "level": 0, "group": True},
    {"label": "Налог.зар", "inflow": 0, "outflow": 1191000, "level": 1},
    {"label": "НДС", "inflow": 0, "outflow": 3579052, "level": 1},
    {"label": "Хоз.Расх", "inflow": 0, "outflow": 1810000, "level": 1},
    {"label": "Цех", "inflow": 0, "outflow": 25234681, "level": 1},
    {"label": "Продажа", "inflow": 240654780, "outflow": 0, "level": 0, "group": True},
    {"label": "раохпер", "inflow": 0, "outflow": 5179133, "level": 0, "group": True},
    {"label": "СальдоКон", "inflow": 0, "outflow": 0, "level": 0, "group": True},
    {"label": "СальдоКон", "inflow": 0, "outflow": 0, "level": 1},
    {"label": "СальдоНач", "inflow": 0, "outflow": 0, "level": 0, "group": True},
    {"label": "СальдоНач", "inflow": 0, "outflow": 0, "level": 1},
    {"label": "сырьё", "inflow": 0, "outflow": 189298810, "level": 0, "group": True},
]

BASE_KPI = {
    "cash": {"start": 110630410, "inflow": 3296487978, "outflow": 3311124078},
    "bank": {"start": 26000000, "inflow": 241000000, "outflow": 227298676},
}


@frappe.whitelist()
def get_dashboard_context():
    return {
        "tabs": TAB_ITEMS,
        "default_filters": {"month": "march"},
        "months": MONTHS,
        "cash_rows": CASH_ROWS,
        "bank_rows": BANK_ROWS,
        "base_kpi": BASE_KPI,
    }
