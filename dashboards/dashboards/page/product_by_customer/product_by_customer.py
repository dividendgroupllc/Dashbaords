from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS


TAB_ITEMS = [
    {"label": "ГЛАВНЫЙ", "route": "/app/main-dashboard"},
    {"label": "ПАНЕЛЬ", "route": "/app/page-dashboard"},
    {"label": "ПРОДАЖА", "route": "/app/sales-dashboard"},
    {"label": "СРАВНЕНИЕ КЛИЕНТОВ", "route": "/app/customer-comparison"},
    {"label": "ТОВАРЫ ПО КЛИЕНТАМ", "route": "/app/product-by-customer", "active": 1},
    {"label": "СРАВНЕНИЕ ПРОДУКТОВ", "route": "/app/product-comparison"},
]


def _get_selected_years(limit: int = 4) -> list[int]:
    rows = frappe.db.sql(
        """
        SELECT DISTINCT YEAR(si.posting_date) AS year
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND si.posting_date IS NOT NULL
        ORDER BY year
        """,
        as_dict=True,
    )

    years = [int(row.year) for row in rows if row.year]
    if limit and len(years) > limit:
        years = years[-limit:]

    if years:
        return years

    return [getdate(today()).year]


def _get_reference_date():
    latest_posting_date = frappe.db.sql(
        """
        SELECT MAX(si.posting_date) AS latest_posting_date
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        """,
        as_dict=True,
    )[0].latest_posting_date

    return getdate(latest_posting_date) if latest_posting_date else getdate(today())


def _get_customer_options(limit: int = 60) -> list[dict[str, str]]:
    rows = frappe.db.sql(
        """
        SELECT
            si.customer AS value,
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент') AS label,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS total_qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND COALESCE(si.customer, '') != ''
        GROUP BY si.customer, COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент')
        ORDER BY total_qty DESC, label ASC
        LIMIT %(limit)s
        """,
        {"limit": limit},
        as_dict=True,
    )

    return [{"value": row.value, "label": row.label} for row in rows]


def _resolve_selected_customer(requested_customer: str | None, customer_options: list[dict[str, str]]) -> str | None:
    if requested_customer and any(option["value"] == requested_customer for option in customer_options):
        return requested_customer

    return None


def _get_selected_customer_label(selected_customer: str | None, customer_options: list[dict[str, str]]) -> str:
    for option in customer_options:
        if option["value"] == selected_customer:
            return option["label"]
    return selected_customer or ""


def _get_product_rows(
    years: list[int],
    month_numbers: list[int],
    selected_customer: str | None,
    item_limit: int = 28,
) -> list[dict[str, Any]]:
    if not years or not month_numbers:
        return []

    year_sql = ", ".join(str(int(year)) for year in years)
    month_sql = ", ".join(str(int(month_no)) for month_no in month_numbers)

    customer_condition = ""
    query_values: dict[str, Any] = {}
    if selected_customer:
        customer_condition = "AND si.customer = %(customer)s"
        query_values["customer"] = selected_customer

    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(si.posting_date) AS month_no,
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар') AS item_label,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS total_qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          {customer_condition}
          AND YEAR(si.posting_date) IN ({year_sql})
          AND MONTH(si.posting_date) IN ({month_sql})
        GROUP BY MONTH(si.posting_date), YEAR(si.posting_date), COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар')
        ORDER BY MONTH(si.posting_date), item_label, YEAR(si.posting_date)
        """,
        query_values,
        as_dict=True,
    )

    monthly_items: dict[int, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        monthly_items[int(row.month_no)][row.item_label][int(row.year)] = flt(row.total_qty)

    month_sections = []
    for month_no in month_numbers:
        item_rows = []
        for item_label, year_map in monthly_items.get(month_no, {}).items():
            values = [flt(year_map.get(year, 0)) for year in years]
            item_rows.append(
                {
                    "label": item_label,
                    "values": values,
                    "total": sum(values),
                    "peak": max(values) if values else 0,
                }
            )

        item_rows = sorted(item_rows, key=lambda row: (-row["total"], -row["peak"], row["label"]))
        selected_items = item_rows[:item_limit]
        month_max = max((max(row["values"]) for row in selected_items), default=0)

        month_sections.append(
            {
                "month_no": month_no,
                "month_label": MONTH_LABELS[month_no - 1],
                "years": [str(year) for year in years],
                "max_value": month_max,
                "items": [{"label": row["label"], "values": row["values"]} for row in selected_items],
                "hidden_item_count": max(len(item_rows) - len(selected_items), 0),
            }
        )

    return month_sections


@frappe.whitelist()
def get_dashboard_context(customer: str | None = None):
    years = _get_selected_years(limit=4)
    reference_date = _get_reference_date()
    month_numbers = list(range(1, reference_date.month + 1))
    customers = _get_customer_options(limit=60)
    selected_customer = _resolve_selected_customer(customer, customers)
    selected_customer_label = _get_selected_customer_label(selected_customer, customers)
    month_sections = _get_product_rows(years, month_numbers, selected_customer)

    return {
        "tabs": TAB_ITEMS,
        "title": "Товары по клиентам",
        "subtitle": "КГ по месяцам, годам и товарам",
        "years": [str(year) for year in years],
        "months": month_sections,
        "customers": customers,
        "selected_customer": selected_customer,
        "selected_customer_label": selected_customer_label,
        "reference_month": MONTH_LABELS[reference_date.month - 1],
        "reference_year": str(reference_date.year),
        "item_limit": 28,
    }
