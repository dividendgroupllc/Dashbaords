from __future__ import annotations

import frappe


YEARS = ["2021", "2023", "2024", "2025"]

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

PRODUCT_ROWS = [
    {"item": "Рулет из мяса птицы коп-вар 0,5", "kg": 9384, "sales": 352204587, "cost": 256208622},
    {"item": "Рулет \"YANGLIK\" коп-вар 0,5", "kg": 6987, "sales": 259713545, "cost": 189312176},
    {"item": "Деликатесная 1-сорт", "kg": 5375, "sales": 211729375, "cost": 146761816},
    {"item": "Докторская особая 1 сорт А", "kg": 4217, "sales": 100148710, "cost": 84613901},
    {"item": "Для завтрака 1 сорт", "kg": 3684, "sales": 85094057, "cost": 71393790},
    {"item": "Сосиски Полоска А", "kg": 3125, "sales": 67269679, "cost": 55419257},
    {"item": "П/к. \"Сервелат\" Говяжий д-50", "kg": 3037, "sales": 109534092, "cost": 84833918},
    {"item": "П/к. \"Rokiza\" Таллинская", "kg": 1770, "sales": 61866910, "cost": 43379568},
    {"item": "П/к. \"Buxanov\" Чимкентская А", "kg": 1613, "sales": 39221754, "cost": 34673579},
    {"item": "П/к. \"Buxanov\" Жорж", "kg": 1535, "sales": 35917684, "cost": 32547775},
    {"item": "Сосиски Тигровый А", "kg": 1444, "sales": 32942199, "cost": 24635559},
    {"item": "Для завтрака 2 сорт 2022", "kg": 1303, "sales": 25423662, "cost": 20519194},
    {"item": "П/к. \"Buxanov\" KO 6", "kg": 1006, "sales": 34382320, "cost": 27522354},
    {"item": "П/к. \"Rokiza\" Ари уг", "kg": 990, "sales": 38033223, "cost": 27397462},
    {"item": "П/к. \"Buxanov\" Украинская", "kg": 926, "sales": 31303244, "cost": 19912045},
    {"item": "П/к. \"Rokiza\" Барака", "kg": 904, "sales": 31035028, "cost": 23459704},
    {"item": "П/к. \"Rokiza\" Таллинская (Особая)", "kg": 901, "sales": 34092819, "cost": 24945280},
    {"item": "Говядина (Премиум) тушенка 325 гр.", "kg": 866, "sales": 28001480, "cost": 15662522},
    {"item": "П/к. \"Buxanov\" Чесночная", "kg": 861, "sales": 20467470, "cost": 17728360},
    {"item": "П/к. \"Кука\" Сервелат д-65", "kg": 797, "sales": 30365370, "cost": 21620716},
    {"item": "Докторская особая Д", "kg": 777, "sales": 23165689, "cost": 14970798},
    {"item": "П/к. \"Buxanov\" Городская", "kg": 760, "sales": 22684553, "cost": 18051991},
    {"item": "П/к. \"Buxanov\" Московская Д-40 (ЖД)", "kg": 750, "sales": 18439495, "cost": 15441760},
    {"item": "П/к. \"Rokiza\" \"особая\"", "kg": 731, "sales": 24785344, "cost": 17362893},
    {"item": "Для завтрака Ишонч", "kg": 615, "sales": 14351128, "cost": 11927067},
    {"item": "Дорожная Золота", "kg": 533, "sales": 11185389, "cost": 10686086},
    {"item": "П/к. \"Buxanov\" Мазали Г", "kg": 520, "sales": 16947320, "cost": 12475840},
    {"item": "Сосиски уважли А 1", "kg": 500, "sales": 9457560, "cost": 8987184},
    {"item": "Сосиски Полоска А (газовый)", "kg": 489, "sales": 11619994, "cost": 8350632},
    {"item": "П/к. \"Rokiza\" Крак", "kg": 486, "sales": 17017573, "cost": 10462738},
    {"item": "П/к. \"Rokiza\" Венгерская д-45", "kg": 478, "sales": 15229335, "cost": 12308866},
    {"item": "П/к. \"Rokiza\" Сервелат A", "kg": 470, "sales": 13985028, "cost": 10519290},
]


@frappe.whitelist()
def get_dashboard_context():
    return {
        "default_filters": {
            "year": "2024",
            "month": "december",
        },
        "years": YEARS,
        "months": MONTHS,
        "product_rows": PRODUCT_ROWS,
    }
