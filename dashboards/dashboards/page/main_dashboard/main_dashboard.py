from __future__ import annotations

import frappe

from dashboards.dashboards.dashboard_data import (
    get_customer_balances,
    get_latest_dashboard_update,
    get_reference_month_label,
)


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


SIDE_METRICS = [
    {"label": "Сред ценa", "metric_key": "avg_price"},
    {"label": "Сред себ", "metric_key": "avg_cost"},
]


@frappe.whitelist()
def get_dashboard_context():
    summary_rows = [
        {
            "label": f"Продажа за {get_reference_month_label()}",
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

    return {
        "tabs": TAB_ITEMS,
        "summary_rows": summary_rows,
        "side_metrics": SIDE_METRICS,
        "balance_label": "Сальдо на конец",
        "dividend_updated_at": get_latest_dashboard_update(),
        "footer_items": [
            {"label": row.client, "value": row.balance}
            for row in get_customer_balances(limit=20)
        ],
    }
