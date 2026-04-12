from __future__ import annotations

import frappe

from dashboards.dashboards.dashboard_data import get_customer_balances


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

@frappe.whitelist()
def get_dashboard_context():
    client_data = get_customer_balances()
    total_balance = sum(item.balance for item in client_data)

    return {
        "tabs": TAB_ITEMS,
        "client_data": client_data,
        "total_balance": total_balance,
    }
