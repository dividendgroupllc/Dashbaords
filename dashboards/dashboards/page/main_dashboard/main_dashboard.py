from __future__ import annotations

import frappe


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard", "active": 1},
    {"label": "DASHBOARD", "route": "/app/page-dashboard"},
    {"label": "KPI", "route": "/app/kpi-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
    {"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
    {"label": "КЛИЕНТ", "route": "/app/client-dashboard"},
    {"label": "ДИВИДЕНТ", "route": "/app/dividend-analysis"},
    {"label": "ЕЖЕМЕСЯЧНО", "route": "/app/monthly-analysis"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
]


SUMMARY_ROWS = [
    {
        "label": "Продажа этот месяц",
        "metric_keys": ["sales_amount", "sales_kg"],
        "metric_labels": ["Сумма прод", "Кг"],
    },
    {
        "label": "Денежные средства",
        "metric_keys": ["cash_total", "bank_total"],
        "metric_labels": ["Касса", "Банк"],
    },
    {
        "label": "Отчет о клиента",
        "metric_keys": ["collections_total", "debtor_total"],
        "metric_labels": ["Поступления", "Дебитор"],
    },
]


SIDE_METRICS = [
    {"label": "Сред ценa", "metric_key": "avg_price"},
    {"label": "Сред себ", "metric_key": "avg_cost"},
]


FOOTER_ITEMS = [
    {"label": "ЧП Ҳаёт", "value": "532,945,000"},
    {"label": "FAYZ SAGBAN OK", "value": "205,009,443"},
    {"label": "ЯТТ Равшан", "value": "176,656,300"},
]


@frappe.whitelist()
def get_dashboard_context():
    return {
        "tabs": TAB_ITEMS,
        "summary_rows": SUMMARY_ROWS,
        "side_metrics": SIDE_METRICS,
        "dividend_updated_at": "18.01.2025 15:40",
        "footer_items": FOOTER_ITEMS,
    }
