from __future__ import annotations

import frappe

from dashboards.dashboards.page.page_dashboard.data import (
    get_avg_check_chart_data,
    get_avg_cost_chart_data,
    get_client_kpi_by_year,
    get_dashboard_years,
    get_dashboard_summary,
    get_default_year,
    get_kg_chart_data,
    get_product_margin_by_year,
    get_regional_summary_by_year,
    get_returns_by_month,
    get_sales_by_month,
)
from dashboards.dashboards.dashboard_data import format_number


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
    {"label": "ПАНЕЛЬ", "route": "/app/page-dashboard", "active": 1},
    {"label": "КПЭ", "route": "/app/kpi-dashboard"},
    {"label": "ЕЖЕДНЕВНО", "route": "/app/daily-dashboard"},
    {"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
    {"label": "КАССА", "route": "/app/cash-dashboard"},
    {"label": "КЛИЕНТ", "route": "/app/client-dashboard"},
    {"label": "ДИВИДЕНДЫ", "route": "/app/dividend-analysis"},
    {"label": "ЕЖЕМЕСЯЧНО", "route": "/app/monthly-analysis"},
    {"label": "ПОСТАВЩИКИ", "route": "/app/supplier-dashboard"},
]

KPI_ITEMS = [
    {"key": "sales_total", "label": "Сумма продаж"},
    {"key": "cost_total", "label": "Себестоимость"},
    {"key": "margin_total", "label": "Маржа"},
    {"key": "rsp_total", "label": "Сумма РСП"},
    {"key": "return_total", "label": "Сумма возвратов"},
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


def _kpi_totals_by_year(years: list[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for year in years:
        summary = get_dashboard_summary(year)
        result[year] = {
            "sales_total": format_number(summary.get("sales_total"), precision=0),
            "cost_total": format_number(summary.get("cost_total"), precision=0),
            "margin_total": format_number(summary.get("margin_total"), precision=0),
            "rsp_total": format_number(summary.get("rsp_total"), precision=0),
            "return_total": format_number(summary.get("return_total"), precision=0),
            "kg_total": format_number(summary.get("kg_total"), precision=0),
            "avg_check": format_number(summary.get("avg_check"), precision=0),
        }
    return result


@frappe.whitelist()
def get_dashboard_context():
    years = get_dashboard_years()
    default_year = get_default_year()

    return {
        "tabs": TAB_ITEMS,
        "kpis": KPI_ITEMS,
        "years": years,
        "default_year": default_year,
        "kpi_totals_by_year": _kpi_totals_by_year(years),
        "chart_data_by_year": {
            year: {
                "price_trend": get_avg_cost_chart_data(year),
                "check_trend": get_avg_check_chart_data(year),
                "kg_trend": get_kg_chart_data(year),
            }
            for year in years
        },
        "sales_by_month_by_year": {year: _rows(get_sales_by_month(year)) for year in years},
        "returns_by_month_by_year": {year: _rows(get_returns_by_month(year)) for year in years},
        "product_margin_by_year": {year: _rows(rows) for year, rows in get_product_margin_by_year().items()},
        "client_kpi_by_year": {year: _rows(rows) for year, rows in get_client_kpi_by_year().items()},
        "regional_summary_by_year": {year: _rows(rows) for year, rows in get_regional_summary_by_year().items()},
    }
