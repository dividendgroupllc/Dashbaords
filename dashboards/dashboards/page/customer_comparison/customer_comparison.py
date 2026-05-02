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
    {"label": "КЛИЕНТ", "route": "/app/client-dashboard"},
    {"label": "СРАВНЕНИЕ КЛИЕНТОВ", "route": "/app/customer-comparison", "active": 1},
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


def _get_customer_comparison_rows(years: list[int], month_numbers: list[int], item_limit: int = 28) -> list[dict[str, Any]]:
    if not years or not month_numbers:
        return []

    year_sql = ", ".join(str(int(year)) for year in years)
    month_sql = ", ".join(str(int(month_no)) for month_no in month_numbers)

    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(si.posting_date) AS month_no,
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент') AS customer_label,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS total_qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND YEAR(si.posting_date) IN ({year_sql})
          AND MONTH(si.posting_date) IN ({month_sql})
        GROUP BY
            MONTH(si.posting_date),
            YEAR(si.posting_date),
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент')
        ORDER BY MONTH(si.posting_date), customer_label, YEAR(si.posting_date)
        """,
        as_dict=True,
    )

    monthly_customers: dict[int, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        monthly_customers[int(row.month_no)][row.customer_label][int(row.year)] = flt(row.total_qty)

    month_sections = []
    for month_no in month_numbers:
        customer_rows = []
        for customer_label, year_map in monthly_customers.get(month_no, {}).items():
            values = [flt(year_map.get(year, 0)) for year in years]
            customer_rows.append(
                {
                    "label": customer_label,
                    "values": values,
                    "total": sum(values),
                    "peak": max(values) if values else 0,
                }
            )

        customer_rows = sorted(customer_rows, key=lambda row: (-row["total"], -row["peak"], row["label"]))
        selected_rows = customer_rows[:item_limit]
        month_max = max((max(row["values"]) for row in selected_rows), default=0)

        month_sections.append(
            {
                "month_no": month_no,
                "month_label": MONTH_LABELS[month_no - 1],
                "years": [str(year) for year in years],
                "max_value": month_max,
                "customers": [
                    {
                        "label": row["label"],
                        "values": row["values"],
                    }
                    for row in selected_rows
                ],
                "hidden_item_count": max(len(customer_rows) - len(selected_rows), 0),
            }
        )

    return month_sections


@frappe.whitelist()
def get_dashboard_context():
    years = _get_selected_years(limit=4)
    reference_date = _get_reference_date()
    month_numbers = list(range(1, reference_date.month + 1))
    month_sections = _get_customer_comparison_rows(years, month_numbers)

    return {
        "tabs": TAB_ITEMS,
        "title": "Сравнение клиентов",
        "subtitle": "КГ по месяцам, годам и клиентам",
        "years": [str(year) for year in years],
        "months": month_sections,
        "reference_month": MONTH_LABELS[reference_date.month - 1],
        "reference_year": str(reference_date.year),
        "item_limit": 28,
    }
