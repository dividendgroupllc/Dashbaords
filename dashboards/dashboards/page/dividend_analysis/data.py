from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import flt, format_datetime, now_datetime, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS, format_number


def get_dividend_years(window: int = 3) -> list[str]:
    rows = frappe.db.sql(
        """
        SELECT DISTINCT YEAR(posting_date) AS year
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date IS NOT NULL
        ORDER BY year
        """,
        as_dict=True,
    )

    years = [int(row.year) for row in rows if row.year]
    if not years:
        current_year = now_datetime().year
        return [str(current_year - 2), str(current_year - 1), str(current_year)]

    last_year = years[-1]
    selected = years[-window:]
    while len(selected) < window:
        selected.insert(0, selected[0] - 1 if selected else last_year)

    return [str(year) for year in selected]


def get_investor_dimension(limit: int = 3) -> list[dict[str, Any]]:
    rows = frappe.db.sql(
        """
        SELECT
            customer,
            COALESCE(NULLIF(customer_name, ''), customer, 'Unknown Investor') AS customer_name,
            SUM(COALESCE(outstanding_amount, 0)) AS outstanding
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        GROUP BY customer, COALESCE(NULLIF(customer_name, ''), customer, 'Unknown Investor')
        ORDER BY outstanding DESC, customer_name ASC
        LIMIT %(limit)s
        """,
        {"limit": limit},
        as_dict=True,
    )

    dimension = []
    for index in range(limit):
        source = rows[index] if index < len(rows) else None
        dimension.append(
            {
                "key": f"investor_{index + 1}",
                "label": f"Investor{index + 1}",
                "customer": source.customer if source else None,
                "display_name": source.customer_name if source else "No data",
                "total_outstanding": flt(source.outstanding) if source else 0,
            }
        )

    return dimension


def _empty_year_month_map(years: list[str]) -> dict[str, dict[int, float]]:
    return {year: {month_no: 0 for month_no in range(1, 13)} for year in years}


def get_total_outstanding_by_years(years: list[str]) -> dict[str, list[str]]:
    values = _empty_year_month_map(years)

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(posting_date) AS year,
            MONTH(posting_date) AS month_no,
            SUM(COALESCE(outstanding_amount, 0)) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND YEAR(posting_date) IN %(years)s
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY YEAR(posting_date), MONTH(posting_date)
        """,
        {"years": tuple(int(year) for year in years)},
        as_dict=True,
    )

    for row in rows:
        values[str(row.year)][row.month_no] = flt(row.amount)

    return {
        year: [format_number(values[year][month_no]) for month_no in range(1, 13)] for year in years
    }


def get_average_outstanding_by_years(years: list[str]) -> dict[str, list[str]]:
    values = _empty_year_month_map(years)

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(posting_date) AS year,
            MONTH(posting_date) AS month_no,
            AVG(COALESCE(outstanding_amount, 0)) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND YEAR(posting_date) IN %(years)s
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY YEAR(posting_date), MONTH(posting_date)
        """,
        {"years": tuple(int(year) for year in years)},
        as_dict=True,
    )

    for row in rows:
        values[str(row.year)][row.month_no] = flt(row.amount)

    return {
        year: [format_number(values[year][month_no], precision=2) for month_no in range(1, 13)] for year in years
    }


def get_invoice_count_by_years(years: list[str]) -> dict[str, list[str]]:
    values = _empty_year_month_map(years)

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(posting_date) AS year,
            MONTH(posting_date) AS month_no,
            COUNT(name) AS invoice_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND YEAR(posting_date) IN %(years)s
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY YEAR(posting_date), MONTH(posting_date)
        """,
        {"years": tuple(int(year) for year in years)},
        as_dict=True,
    )

    for row in rows:
        values[str(row.year)][row.month_no] = flt(row.invoice_count)

    return {
        year: [format_number(values[year][month_no]) for month_no in range(1, 13)] for year in years
    }


def get_investor_totals_by_years(years: list[str], investors: list[dict[str, Any]]) -> dict[str, list[str]]:
    result = {investor["key"]: {year: 0 for year in years} for investor in investors}
    customer_map = {investor["customer"]: investor["key"] for investor in investors if investor.get("customer")}

    if not customer_map:
        return {investor["key"]: [format_number(0) for _ in years] for investor in investors}

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(posting_date) AS year,
            customer,
            SUM(COALESCE(outstanding_amount, 0)) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND YEAR(posting_date) IN %(years)s
          AND customer IN %(customers)s
        GROUP BY YEAR(posting_date), customer
        ORDER BY YEAR(posting_date), customer
        """,
        {
            "years": tuple(int(year) for year in years),
            "customers": tuple(customer_map.keys()),
        },
        as_dict=True,
    )

    for row in rows:
        key = customer_map.get(row.customer)
        if key:
            result[key][str(row.year)] = flt(row.amount)

    return {
        investor["key"]: [format_number(result[investor["key"]][year]) for year in years] for investor in investors
    }


def get_investor_monthly_totals_by_years(years: list[str], investors: list[dict[str, Any]]) -> dict[str, list[str]]:
    values = _empty_year_month_map(years)
    customers = tuple(investor["customer"] for investor in investors if investor.get("customer"))

    if not customers:
        return {
            year: [format_number(values[year][month_no]) for month_no in range(1, 13)] for year in years
        }

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(posting_date) AS year,
            MONTH(posting_date) AS month_no,
            SUM(COALESCE(outstanding_amount, 0)) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND YEAR(posting_date) IN %(years)s
          AND customer IN %(customers)s
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY YEAR(posting_date), MONTH(posting_date)
        """,
        {
            "years": tuple(int(year) for year in years),
            "customers": customers,
        },
        as_dict=True,
    )

    for row in rows:
        values[str(row.year)][row.month_no] = flt(row.amount)

    return {
        year: [format_number(values[year][month_no]) for month_no in range(1, 13)] for year in years
    }


def get_investor_monthly_breakdown(years: list[str], investors: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result = {year: [] for year in years}
    customer_map = {investor["customer"]: investor["key"] for investor in investors if investor.get("customer")}
    base_map: dict[str, dict[int, dict[str, float]]] = {
        year: {
            month_no: {investor["key"]: 0 for investor in investors}
            for month_no in range(1, 13)
        }
        for year in years
    }

    if customer_map:
        rows = frappe.db.sql(
            """
            SELECT
                YEAR(posting_date) AS year,
                MONTH(posting_date) AS month_no,
                customer,
                SUM(COALESCE(outstanding_amount, 0)) AS amount
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND COALESCE(is_return, 0) = 0
              AND YEAR(posting_date) IN %(years)s
              AND customer IN %(customers)s
            GROUP BY YEAR(posting_date), MONTH(posting_date), customer
            ORDER BY YEAR(posting_date), MONTH(posting_date), customer
            """,
            {
                "years": tuple(int(year) for year in years),
                "customers": tuple(customer_map.keys()),
            },
            as_dict=True,
        )

        for row in rows:
            investor_key = customer_map.get(row.customer)
            if investor_key:
                base_map[str(row.year)][row.month_no][investor_key] = flt(row.amount)

    for year in years:
        total_year = {investor["key"]: 0 for investor in investors}
        for month_no in range(1, 13):
            investor_values = base_map[year][month_no]
            row_total = sum(investor_values.values())
            for key, value in investor_values.items():
                total_year[key] += value

            result[year].append(
                {
                    "month": MONTH_LABELS[month_no - 1],
                    "values": {key: format_number(value) for key, value in investor_values.items()},
                    "total": format_number(row_total),
                }
            )

        result[year].append(
            {
                "month": "Total",
                "values": {key: format_number(value) for key, value in total_year.items()},
                "total": format_number(sum(total_year.values())),
                "is_total": True,
            }
        )

    return result


def get_dashboard_snapshot() -> dict[str, Any]:
    years = get_dividend_years()
    investors = get_investor_dimension()
    latest_year = years[-1]

    return {
        "years": years,
        "selected_year": latest_year,
        "months": MONTH_LABELS,
        "investors": investors,
        "outstanding_by_year": get_total_outstanding_by_years(years),
        "average_by_year": get_average_outstanding_by_years(years),
        "invoice_count_by_year": get_invoice_count_by_years(years),
        "investor_totals_by_year": get_investor_totals_by_years(years, investors),
        "investor_monthly_totals_by_year": get_investor_monthly_totals_by_years(years, investors),
        "investor_monthly_breakdown": get_investor_monthly_breakdown(years, investors),
        "generated_at": format_datetime(now_datetime()),
        "reference_date": today(),
    }
