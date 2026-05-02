from __future__ import annotations

import frappe


MAIN_NUMBER_CARDS = [
    ("Main Dashboard Sales Amount", "dashboards.dashboards.page.main_dashboard.data.get_sales_amount", "#48e61c"),
    ("Main Dashboard Sales Kg", "dashboards.dashboards.page.main_dashboard.data.get_sales_kg", "#48e61c"),
    ("Main Dashboard Cash Total", "dashboards.dashboards.page.main_dashboard.data.get_cash_total", "#48e61c"),
    ("Main Dashboard Bank Total", "dashboards.dashboards.page.main_dashboard.data.get_bank_total", "#48e61c"),
    ("Main Dashboard Collections", "dashboards.dashboards.page.main_dashboard.data.get_collections_total", "#48e61c"),
    ("Main Dashboard Debtor Total", "dashboards.dashboards.page.main_dashboard.data.get_debtor_total", "#48e61c"),
    ("Main Dashboard Average Price", "dashboards.dashboards.page.main_dashboard.data.get_average_price", "#48e61c"),
    ("Main Dashboard Average Cost", "dashboards.dashboards.page.main_dashboard.data.get_average_cost", "#48e61c"),
    ("Main Dashboard Dividend Total", "dashboards.dashboards.page.main_dashboard.data.get_dividend_total", "#ff6d87"),
]

MAIN_NUMBER_CARD_LABELS = {
    "Main Dashboard Sales Amount": "Сумма продаж",
    "Main Dashboard Sales Kg": "Продажи, кг",
    "Main Dashboard Cash Total": "Касса",
    "Main Dashboard Bank Total": "Банк",
    "Main Dashboard Collections": "Поступления",
    "Main Dashboard Debtor Total": "Дебиторская задолженность",
    "Main Dashboard Average Price": "Средняя цена",
    "Main Dashboard Average Cost": "Средняя себестоимость",
    "Main Dashboard Dividend Total": "Сальдо",
}

MAIN_CHART_SOURCES = [
    ("Main Dashboard Timeline Source", "Dashboards"),
    ("Main Dashboard Monthly Snapshot Source", "Dashboards"),
]

MAIN_CHARTS = [
    ("Main Dashboard Timeline", "Main Dashboard Timeline Source", "Bar", 1),
    ("Main Dashboard Monthly Snapshot", "Main Dashboard Monthly Snapshot Source", "Bar", 0),
]

DASHBOARD_NUMBER_CARDS = [
    ("Dashboard Sales Total", "dashboards.dashboards.page.page_dashboard.data.get_sales_total", "#16a327"),
    ("Dashboard Cost Total", "dashboards.dashboards.page.page_dashboard.data.get_cost_total", "#16a327"),
    ("Dashboard Margin Total", "dashboards.dashboards.page.page_dashboard.data.get_margin_total", "#16a327"),
    ("Dashboard RSP Total", "dashboards.dashboards.page.page_dashboard.data.get_rsp_total", "#16a327"),
    ("Dashboard Return Total", "dashboards.dashboards.page.page_dashboard.data.get_return_total", "#16a327"),
    ("Dashboard Kg Total", "dashboards.dashboards.page.page_dashboard.data.get_kg_total", "#16a327"),
    ("Dashboard Avg Check", "dashboards.dashboards.page.page_dashboard.data.get_avg_check", "#16a327"),
]

DASHBOARD_CHART_SOURCES = [
    ("Dashboard Avg Cost Source", "Dashboards"),
    ("Dashboard Avg Check Source", "Dashboards"),
    ("Dashboard Product Kg Source", "Dashboards"),
]

DASHBOARD_CHARTS = [
    ("Dashboard Avg Cost Chart", "Dashboard Avg Cost Source", "Bar"),
    ("Dashboard Avg Check Chart", "Dashboard Avg Check Source", "Bar"),
    ("Dashboard Product Kg Chart", "Dashboard Product Kg Source", "Bar"),
]


def execute():
    for source_name, module in MAIN_CHART_SOURCES + DASHBOARD_CHART_SOURCES:
        upsert_doc(
            "Dashboard Chart Source",
            source_name,
            {
                "source_name": source_name,
                "module": module,
                "timeseries": 0,
            },
        )

    for chart_name, source_name, chart_type, *rest in MAIN_CHARTS:
        upsert_doc(
            "Dashboard Chart",
            chart_name,
            {
                "chart_name": chart_name,
                "chart_type": "Custom",
                "source": source_name,
                "document_type": "Page",
                "module": "Dashboards",
                "type": chart_type,
                "is_public": 1,
                "show_values_over_chart": rest[0] if rest else 0,
                "filters_json": "[]",
                "roles": [{"role": "Desk User"}, {"role": "System Manager"}],
            },
            child_tables={"roles"},
        )

    for chart_name, source_name, chart_type in DASHBOARD_CHARTS:
        upsert_doc(
            "Dashboard Chart",
            chart_name,
            {
                "chart_name": chart_name,
                "chart_type": "Custom",
                "source": source_name,
                "document_type": "Page",
                "module": "Dashboards",
                "type": chart_type,
                "is_public": 1,
                "show_values_over_chart": 0,
                "filters_json": "[]",
                "roles": [{"role": "Desk User"}, {"role": "System Manager"}],
            },
            child_tables={"roles"},
        )

    for card_name, method, color in MAIN_NUMBER_CARDS + DASHBOARD_NUMBER_CARDS:
        upsert_doc(
            "Number Card",
            card_name,
            {
                "label": MAIN_NUMBER_CARD_LABELS.get(card_name, card_name),
                "type": "Custom",
                "method": method,
                "document_type": "Page",
                "module": "Dashboards",
                "is_public": 1,
                "show_percentage_stats": 0,
                "color": color,
            },
        )


def upsert_doc(doctype, name, values, child_tables=None):
    child_tables = child_tables or set()
    existing_name = frappe.db.exists(doctype, name)

    if existing_name:
        doc = frappe.get_doc(doctype, existing_name)
    else:
        doc = frappe.new_doc(doctype)
        doc.name = name

    for fieldname, value in values.items():
        if fieldname in child_tables:
            doc.set(fieldname, value)
        else:
            doc.set(fieldname, value)

    if existing_name:
        doc.save(ignore_permissions=True)
    else:
        doc.insert(ignore_permissions=True)
