from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import cint, flt

from dashboards.dashboards.dashboard_data import MONTH_LABELS, format_number, get_reference_month_date


ITEM_ROW_LIMIT = 40
CUSTOMER_ROW_LIMIT = 18


def _get_years(limit: int = 4) -> list[int]:
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

    years = [cint(row.year) for row in rows if row.year]
    if limit and len(years) > limit:
        years = years[-limit:]
    return years


def _format_int(value: float | int) -> str:
    return format_number(round(flt(value)), precision=0)


def _get_product_rows(years: list[int], month_limit: int) -> list[dict[str, Any]]:
    if not years:
        return []

    rows = frappe.db.sql(
        """
        SELECT
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item') AS item_name,
            YEAR(si.posting_date) AS year,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND YEAR(si.posting_date) IN %(years)s
          AND MONTH(si.posting_date) <= %(month_limit)s
        GROUP BY COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item'), YEAR(si.posting_date)
        """,
        {"years": tuple(years), "month_limit": month_limit},
        as_dict=True,
    )

    grouped: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    totals_by_year = defaultdict(float)

    for row in rows:
        label = row.item_name or "Unknown Item"
        year = cint(row.year)
        qty = flt(row.qty)
        grouped[label][year] += qty
        totals_by_year[year] += qty

    ordered_labels = sorted(grouped, key=lambda label: (-sum(grouped[label].values()), label))[:ITEM_ROW_LIMIT]
    result = []

    for label in ordered_labels:
        values = [grouped[label].get(year, 0) for year in years]
        total = sum(values)
        result.append(
            {
                "label": label,
                "values": [_format_int(value) if value else "" for value in values],
                "total": _format_int(total) if total else "",
            }
        )

    grand_total = sum(totals_by_year.values())
    result.append(
        {
            "label": "Total",
            "values": [_format_int(totals_by_year.get(year, 0)) if totals_by_year.get(year, 0) else "" for year in years],
            "total": _format_int(grand_total) if grand_total else "",
            "is_total": True,
        }
    )

    return result


def _get_customer_year_tables(years: list[int], month_limit: int) -> list[dict[str, Any]]:
    if not years:
        return []

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            MONTH(si.posting_date) AS month_no,
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client') AS customer_name,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND YEAR(si.posting_date) IN %(years)s
          AND MONTH(si.posting_date) <= %(month_limit)s
        GROUP BY YEAR(si.posting_date), MONTH(si.posting_date), COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client')
        """,
        {"years": tuple(years), "month_limit": month_limit},
        as_dict=True,
    )

    grouped: dict[int, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    monthly_totals: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))

    for row in rows:
        year = cint(row.year)
        month_no = cint(row.month_no)
        label = row.customer_name or "Unknown Client"
        qty = flt(row.qty)
        grouped[year][label][month_no] += qty
        monthly_totals[year][month_no] += qty

    tables = []
    month_numbers = list(range(1, month_limit + 1))
    month_labels = MONTH_LABELS[:month_limit]

    for year in years:
        customer_map = grouped.get(year, {})
        ordered_labels = sorted(customer_map, key=lambda label: (-sum(customer_map[label].values()), label))[:CUSTOMER_ROW_LIMIT]
        rows_for_year = []

        for label in ordered_labels:
            values = [customer_map[label].get(month_no, 0) for month_no in month_numbers]
            total = sum(values)
            rows_for_year.append(
                {
                    "label": label,
                    "values": [_format_int(value) if value else "" for value in values],
                    "total": _format_int(total) if total else "",
                }
            )

        total_row_values = [monthly_totals[year].get(month_no, 0) for month_no in month_numbers]
        rows_for_year.append(
            {
                "label": "Total",
                "values": [_format_int(value) if value else "" for value in total_row_values],
                "total": _format_int(sum(total_row_values)) if sum(total_row_values) else "",
                "is_total": True,
            }
        )

        tables.append(
            {
                "year": year,
                "title": f"Клиент {year} кг",
                "months": month_labels,
                "rows": rows_for_year,
            }
        )

    return tables


def get_dashboard_context() -> dict[str, Any]:
    reference_date = get_reference_month_date()
    years = _get_years(limit=4)
    customer_years = years[-2:]
    month_limit = cint(reference_date.month) or 1

    return {
        "title": "Comparison by Product",
        "years": [str(year) for year in years],
        "reference_month": MONTH_LABELS[month_limit - 1],
        "reference_year": str(reference_date.year),
        "product_title": "Предметы кг",
        "product_rows": _get_product_rows(years, month_limit),
        "customer_tables": _get_customer_year_tables(customer_years, month_limit),
    }
