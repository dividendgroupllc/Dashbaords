from __future__ import annotations

import json
from pathlib import Path

import frappe

from dashboards.dashboards.page.page_dashboard.data import (
    get_avg_check_chart_data,
    get_avg_cost_chart_data,
    get_client_kpi_rows,
    get_default_period,
    get_dashboard_years,
    get_dashboard_summary,
    get_default_year,
    get_kg_chart_data,
    get_kpi_client_table_rows,
    get_product_margin_rows,
    get_regional_map_data,
    get_regional_summary_rows,
)
from dashboards.dashboards.dashboard_data import MONTH_LABELS, format_number


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
    {"label": "ПАНЕЛЬ", "route": "/app/page-dashboard", "active": 1},
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

_GEOJSON_PATH = Path(
    frappe.get_app_path("dashboards", "public", "geojson", "uzbekistan_regions.clean.geojson")
)


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


def _format_kpi_totals(year: str, month: str | None = None) -> dict[str, str]:
    summary = get_dashboard_summary(year, month)
    return {
        "sales_total": format_number(summary.get("sales_total"), precision=0),
        "cost_total": format_number(summary.get("cost_total"), precision=0),
        "margin_total": format_number(summary.get("margin_total"), precision=0),
        "rsp_total": format_number(summary.get("rsp_total"), precision=0),
        "return_total": format_number(summary.get("return_total"), precision=0),
        "kg_total": format_number(summary.get("kg_total"), precision=0),
        "avg_check": format_number(summary.get("avg_check"), precision=0),
    }


@frappe.whitelist()
def get_dashboard_context(year: str | None = None, month: str | None = None):
    years = get_dashboard_years()
    default_year = get_default_year()
    selected_year = str(year) if year in years else default_year
    selected_month = month if month in MONTH_LABELS else None

    return {
        "tabs": TAB_ITEMS,
        "kpis": KPI_ITEMS,
        "years": years,
        "months": MONTH_LABELS,
        "default_year": default_year,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "default_month_by_year": {item_year: get_default_period(item_year)[1] for item_year in years},
        "kpi_totals": _format_kpi_totals(selected_year, selected_month),
        "chart_data": {
            "price_trend": get_avg_cost_chart_data(selected_year),
            "check_trend": get_avg_check_chart_data(selected_year),
            "kg_trend": get_kg_chart_data(selected_year),
        },
        "product_margin_rows": _rows(get_product_margin_rows(selected_year, selected_month)),
        "product_margin_title": (
            f"Данные за {selected_month} {selected_year}" if selected_month else f"Данные за {selected_year} год"
        ),
        "client_kpi_rows": _rows(get_client_kpi_rows(selected_year, selected_month)),
        "kpi_client_rows": _rows(get_kpi_client_table_rows(selected_year, selected_month)),
        "kpi_client_title": (
            f"Данные за {selected_month} {selected_year}" if selected_month else f"Данные за {selected_year} год"
        ),
        "regional_summary_rows": _rows(get_regional_summary_rows(selected_year, selected_month)),
        "regional_map": get_regional_map_data(selected_year, selected_month),
    }


@frappe.whitelist()
def get_regions_geojson():
    return json.loads(_GEOJSON_PATH.read_text(encoding="utf-8"))
