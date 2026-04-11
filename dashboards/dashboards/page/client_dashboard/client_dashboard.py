from __future__ import annotations

import frappe


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
    {"label": "DASHBOARD", "route": "/app/page-dashboard"},
    {"label": "KPI", "route": "/app/kpi-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
    {"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
    {"label": "КЛИЕНТ", "route": "/app/client-dashboard", "active": 1},
    {"label": "ДИВИДЕНТ", "route": "/app/dividend-analysis"},
    {"label": "КЛИЕНТ", "route": "/app/customer-comparison"},
    {"label": "ЕЖЕМЕСЯЧНО", "route": "/app/monthly-analysis"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
]


CLIENT_DATA = [
    {"client": "ЧП Ҳаёт", "balance": 532945000},
    {"client": "FAYZ SAGBAN OK", "balance": 205009443},
    {"client": "ЯТТ Равшан", "balance": 176656354},
    {"client": "ЯТТ Норматов Гиёсжон Уктам угли", "balance": 141286435},
    {"client": "ЧП Махмудхон", "balance": 136110888},
    {"client": "ЯТТ Жавлон", "balance": 108916235},
    {"client": "Kopea", "balance": 107812603},
    {"client": "Мухиддин", "balance": 103204076},
    {"client": "ЯТТ Илхом", "balance": 95668030},
    {"client": "ЯТТ Орзубек", "balance": 64996938},
    {"client": "ЯТТ Холбек", "balance": 63824362},
    {"client": "ЧП Ботир", "balance": 56650343},
    {"client": "ЧП Жамшид", "balance": 45891024},
    {"client": "ЯТТ Мурадов Алихон", "balance": 38175962},
    {"client": "ООО Самарканд Дарвоза", "balance": 31990522},
    {"client": "ЯТТ Алишер", "balance": 25000000},
    {"client": "ЧП Гафуров Тилла Хушмаматович", "balance": 19328624},
    {"client": "Ориф ака", "balance": 11367770},
    {"client": "Разний", "balance": 10166272},
    {"client": "ЯТТ Рустам", "balance": 7335303},
    {"client": "ЧП Жахонгир", "balance": 4465555},
    {"client": "Зокиржонов Илхом", "balance": 3772837},
    {"client": "ЯТТ Ойбек", "balance": 2876329},
    {"client": "ЯТТ Аброр", "balance": 2688927},
]


@frappe.whitelist()
def get_dashboard_context():
    # Sort by balance descending
    sorted_data = sorted(CLIENT_DATA, key=lambda x: x["balance"], reverse=True)
    total_balance = sum(item["balance"] for item in sorted_data)

    return {
        "tabs": TAB_ITEMS,
        "client_data": sorted_data,
        "total_balance": total_balance,
    }
