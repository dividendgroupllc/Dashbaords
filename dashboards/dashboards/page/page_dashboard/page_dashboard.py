from __future__ import annotations

import frappe

from dashboards.dashboards.page.page_dashboard.data import (
    get_client_kpi_by_year,
    get_dashboard_years,
    get_default_year,
    get_product_margin_by_year,
    get_regional_summary_by_year,
    get_returns_by_month,
    get_sales_by_month,
)


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
    {"label": "DASHBOARD", "route": "/app/page-dashboard", "active": 1},
    {"label": "KPI", "route": "/app/kpi-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
    {"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
    {"label": "КЛИЕНТ", "route": "/app/client-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/monthly-analysis"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
]

KPI_ITEMS = [
    {"key": "sales_total", "label": "Сумма продажа"},
    {"key": "cost_total", "label": "Сумма себестоимость", "subtext": "Савдо"},
    {"key": "margin_total", "label": "Маржа", "subtext": "Возврат дей-ай суммдаа"},
    {"key": "rsp_total", "label": "РСП сумма"},
    {"key": "return_total", "label": "Возврат сумма"},
    {"key": "kg_total", "label": "КГ"},
    {"key": "avg_check", "label": "Сред.чек"},
]


def _rows(data):
    rows = []
    for item in data:
        values = item[:]
        is_total = False
        if len(values) and values[-1] is True:
            values = values[:-1]
            is_total = True
        rows.append({"values": values, "is_total": is_total})
    return rows


@frappe.whitelist()
def get_dashboard_context():
    years = get_dashboard_years()
    default_year = get_default_year()

    return {
        "tabs": TAB_ITEMS,
        "kpis": KPI_ITEMS,
        "years": years,
        "default_year": default_year,
        "sales_by_month_by_year": {year: _rows(get_sales_by_month(year)) for year in years},
        "returns_by_month_by_year": {year: _rows(get_returns_by_month(year)) for year in years},
        "product_margin_by_year": {year: _rows(rows) for year, rows in get_product_margin_by_year().items()},
        "client_kpi_by_year": {year: _rows(rows) for year, rows in get_client_kpi_by_year().items()},
        "regional_summary_by_year": {year: _rows(rows) for year, rows in get_regional_summary_by_year().items()},
    }
