from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint, flt, format_datetime, get_first_day, get_last_day, getdate, now_datetime, today


MONTH_LABELS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def get_reference_month_date():
    latest_posting_date = frappe.db.sql(
        """
        SELECT MAX(posting_date) AS latest_posting_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        """,
        as_dict=True,
    )[0].latest_posting_date

    return getdate(latest_posting_date) if latest_posting_date else getdate(today())


def get_reference_month_range() -> tuple[str, str]:
    reference_date = get_reference_month_date()
    return str(get_first_day(reference_date)), str(get_last_day(reference_date))


def get_reference_month_label() -> str:
    reference_date = get_reference_month_date()
    return reference_date.strftime("%m.%Y")


def format_number(value: Any, precision: int = 0) -> str:
    number = flt(value)
    formatted = f"{number:,.{precision}f}".replace(",", " ")
    if precision > 0:
        formatted = formatted.rstrip("0").rstrip(".")
    else:
        formatted = formatted.split(".")[0]
    return formatted


def get_monthly_sales_kg(year_limit: int = 4) -> list[dict[str, Any]]:
    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            MONTH(si.posting_date) AS month_no,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS total_kg
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), MONTH(si.posting_date)
        ORDER BY YEAR(si.posting_date), MONTH(si.posting_date)
        """,
        as_dict=True,
    )

    years = sorted({row.year for row in rows if row.year})
    if year_limit and len(years) > year_limit:
        years = years[-year_limit:]

    monthly_map = {(row.year, row.month_no): flt(row.total_kg) for row in rows if row.year in years}
    result = []
    for year in years:
        values = [round(monthly_map.get((year, month_no), 0)) for month_no in range(1, 13)]
        result.append({"year": year, "values": values})

    return result


def get_monthly_sales_amount(year_limit: int = 2) -> list[dict[str, Any]]:
    rows = frappe.db.sql(
        """
        SELECT
            YEAR(posting_date) AS year,
            MONTH(posting_date) AS month_no,
            SUM(COALESCE(base_net_total, net_total, 0)) AS total_amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        GROUP BY YEAR(posting_date), MONTH(posting_date)
        ORDER BY YEAR(posting_date), MONTH(posting_date)
        """,
        as_dict=True,
    )

    years = sorted({row.year for row in rows if row.year})
    if year_limit and len(years) > year_limit:
        years = years[-year_limit:]

    monthly_map = {(row.year, row.month_no): flt(row.total_amount) for row in rows if row.year in years}
    result = []
    for year in reversed(years):
        values = [round(monthly_map.get((year, month_no), 0)) for month_no in range(1, 13)]
        result.append({"year": year, "values": values})

    return result


def get_current_month_sales_summary() -> dict[str, float]:
    start_date, end_date = get_reference_month_range()

    invoice_totals = frappe.db.sql(
        """
        SELECT
            SUM(COALESCE(base_net_total, net_total, 0)) AS sales_amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND posting_date BETWEEN %(start_date)s AND %(end_date)s
        """,
        {"start_date": start_date, "end_date": end_date},
        as_dict=True,
    )[0]

    item_totals = frappe.db.sql(
        """
        SELECT
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS sales_kg,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS total_cost
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND si.posting_date BETWEEN %(start_date)s AND %(end_date)s
        """,
        {"start_date": start_date, "end_date": end_date},
        as_dict=True,
    )[0]

    money_balances = frappe.db.sql(
        """
        SELECT
            acc.account_type,
            SUM(COALESCE(gle.debit, 0) - COALESCE(gle.credit, 0)) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
          AND acc.is_group = 0
          AND acc.account_type IN ('Cash', 'Bank')
        GROUP BY acc.account_type
        """,
        as_dict=True,
    )

    collections = frappe.db.sql(
        """
        SELECT
            SUM(
                COALESCE(base_received_amount, 0) + CASE
                    WHEN COALESCE(base_received_amount, 0) = 0 THEN COALESCE(base_paid_amount, 0)
                    ELSE 0
                END
            ) AS collections_total
        FROM `tabPayment Entry`
        WHERE docstatus = 1
          AND payment_type = 'Receive'
          AND posting_date BETWEEN %(start_date)s AND %(end_date)s
        """,
        {"start_date": start_date, "end_date": end_date},
        as_dict=True,
    )[0]

    debtor_total = frappe.db.sql(
        """
        SELECT SUM(COALESCE(outstanding_amount, 0)) AS debtor_total
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND COALESCE(outstanding_amount, 0) > 0
        """,
        as_dict=True,
    )[0]

    balances = {row.account_type: flt(row.balance) for row in money_balances}
    sales_kg = flt(item_totals.sales_kg)
    sales_amount = flt(invoice_totals.sales_amount)
    total_cost = flt(item_totals.total_cost)

    return {
        "sales_amount": sales_amount,
        "sales_kg": sales_kg,
        "cash_total": flt(balances.get("Cash")),
        "bank_total": flt(balances.get("Bank")),
        "collections_total": flt(collections.collections_total),
        "debtor_total": flt(debtor_total.debtor_total),
        "avg_price": sales_amount / sales_kg if sales_kg else 0,
        "avg_cost": total_cost / sales_kg if sales_kg else 0,
        "balance_total": flt(debtor_total.debtor_total),
    }


def get_sales_amount_timeline(year_limit: int = 2) -> dict[str, list[Any]]:
    labels = []
    values = []

    for row in get_monthly_sales_amount(year_limit=year_limit):
        for month_name, month_value in zip(MONTH_LABELS, row["values"]):
            labels.append(f"{month_name}\n{row['year']}")
            values.append(month_value)

    return {"labels": labels, "values": values}


def get_customer_balances(limit: int | None = None) -> list[dict[str, Any]]:
    limit = cint(limit)
    limit_clause = f"LIMIT {limit}" if limit else ""

    return frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(customer_name, ''), customer) AS client,
            customer,
            SUM(COALESCE(outstanding_amount, 0)) AS balance
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND COALESCE(outstanding_amount, 0) > 0
        GROUP BY customer, customer_name
        ORDER BY balance DESC
        {limit_clause}
        """,
        as_dict=True,
    )


def get_latest_dashboard_update() -> str:
    latest_posting_date = frappe.db.sql(
        """
        SELECT MAX(posting_date) AS latest_posting_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        """,
        as_dict=True,
    )[0].latest_posting_date

    if latest_posting_date:
        return format_datetime(latest_posting_date, "dd.MM.yyyy")

    return format_datetime(now_datetime(), "dd.MM.yyyy HH:mm")
