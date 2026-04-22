from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import MONTH_LABELS, format_number


def get_dashboard_years() -> list[str]:
    years = frappe.db.sql(
        """
        SELECT DISTINCT YEAR(posting_date) AS year
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date IS NOT NULL
        ORDER BY year
        """,
        as_dict=True,
    )

    values = [str(row.year) for row in years if row.year]
    if values:
        return values

    return [str(getdate(today()).year)]


def get_default_year() -> str:
    return get_dashboard_years()[-1]


def _year_filter_clause(year: str | None, alias: str = "") -> tuple[str, dict[str, Any]]:
    prefix = f"{alias}." if alias else ""
    filters: dict[str, Any] = {}
    clause = ""

    if year:
        clause = f" AND YEAR({prefix}posting_date) = %(year)s"
        filters["year"] = int(year)

    return clause, filters


def _empty_month_map() -> dict[int, float]:
    return {month_no: 0 for month_no in range(1, 13)}


def _resolve_year(filters=None) -> str:
    if filters:
        parsed_filters = frappe.parse_json(filters) if not isinstance(filters, dict) else filters
        year = parsed_filters.get("year") if parsed_filters else None
        if year:
            return str(year)

    return get_default_year()


def get_dashboard_summary(year: str | None = None) -> dict[str, float]:
    invoice_clause, invoice_params = _year_filter_clause(year)
    item_clause, item_params = _year_filter_clause(year, alias="si")

    invoice_totals = frappe.db.sql(
        f"""
        SELECT
            SUM(CASE WHEN COALESCE(is_return, 0) = 0 THEN COALESCE(base_net_total, net_total, 0) ELSE 0 END) AS sales_total,
            SUM(CASE WHEN COALESCE(is_return, 0) = 1 THEN ABS(COALESCE(base_net_total, net_total, 0)) ELSE 0 END) AS return_total,
            SUM(CASE WHEN COALESCE(is_return, 0) = 0 THEN ABS(COALESCE(base_total_taxes_and_charges, total_taxes_and_charges, 0)) ELSE 0 END) AS rsp_total,
            COUNT(CASE WHEN COALESCE(is_return, 0) = 0 THEN name END) AS invoice_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        {invoice_clause}
        """,
        invoice_params,
        as_dict=True,
    )[0]

    item_totals = frappe.db.sql(
        f"""
        SELECT
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS kg_total,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_total
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        {item_clause}
        """,
        item_params,
        as_dict=True,
    )[0]

    sales_total = flt(invoice_totals.sales_total)
    cost_total = flt(item_totals.cost_total)
    margin_total = sales_total - cost_total
    invoice_count = flt(invoice_totals.invoice_count)

    return {
        "sales_total": sales_total,
        "cost_total": cost_total,
        "margin_total": margin_total,
        "rsp_total": flt(invoice_totals.rsp_total),
        "return_total": flt(invoice_totals.return_total),
        "kg_total": flt(item_totals.kg_total),
        "avg_check": sales_total / invoice_count if invoice_count else 0,
    }


def _format_summary_value(key: str, year: str | None = None) -> str:
    return format_number(get_dashboard_summary(year).get(key), precision=0)


def get_sales_by_month(year: str | None = None) -> list[list[str]]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year)
    month_map = _empty_month_map()

    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(posting_date) AS month_no,
            SUM(COALESCE(base_net_total, net_total, 0)) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        {clause}
        GROUP BY MONTH(posting_date)
        ORDER BY MONTH(posting_date)
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        month_map[row.month_no] = flt(row.amount)

    return [[MONTH_LABELS[month_no - 1], format_number(month_map[month_no])] for month_no in range(1, 13)]


def get_returns_by_month(year: str | None = None) -> list[list[str]]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year)
    month_map = _empty_month_map()

    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(posting_date) AS month_no,
            SUM(ABS(COALESCE(base_net_total, net_total, 0))) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 1
        {clause}
        GROUP BY MONTH(posting_date)
        ORDER BY MONTH(posting_date)
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        month_map[row.month_no] = flt(row.amount)

    return [[MONTH_LABELS[month_no - 1], format_number(month_map[month_no])] for month_no in range(1, 13)]


def get_product_margin_by_year(limit: int | None = None) -> dict[str, list[list[str | bool]]]:
    result = {year: [] for year in get_dashboard_years()}

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item') AS item_label,
            SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Unknown Item')
        """,
        as_dict=True,
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = str(row.year)
        sales_amount = flt(row.sales_amount)
        cost_amount = flt(row.cost_amount)
        margin_amount = sales_amount - cost_amount
        grouped[year].append(
            {
                "label": row.item_label,
                "sales": sales_amount,
                "margin": margin_amount,
                "profitability": (margin_amount / sales_amount * 100) if sales_amount else 0,
            }
        )

    for year, values in grouped.items():
        sorted_values = sorted(values, key=lambda row: row["margin"], reverse=True)
        top_rows = [
            [row["label"], format_number(row["margin"]), f"{row['profitability']:.1f}%".replace(".", ",")]
            for row in sorted_values[:limit]
        ]

        total_margin = sum(row["margin"] for row in values)
        total_sales = sum(row["sales"] for row in values)
        total_profitability = (total_margin / total_sales * 100) if total_sales else 0
        top_rows.append(
            ["Total", format_number(total_margin), f"{total_profitability:.1f}%".replace(".", ","), True]
        )
        result[year] = top_rows

    return result


def get_client_kpi_by_year(limit: int | None = None) -> dict[str, list[list[str | bool]]]:
    result = {year: [] for year in get_dashboard_years()}

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client') AS client,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Unknown Client')
        """,
        as_dict=True,
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = str(row.year)
        sales_amount = flt(row.sales_amount)
        cost_amount = flt(row.cost_amount)
        margin_amount = sales_amount - cost_amount
        grouped[year].append(
            {
                "client": row.client,
                "qty": flt(row.qty_total),
                "sales": sales_amount,
                "margin": margin_amount,
                "profitability": (margin_amount / sales_amount * 100) if sales_amount else 0,
            }
        )

    for year, values in grouped.items():
        sorted_values = sorted(values, key=lambda row: row["sales"], reverse=True)
        selected_values = sorted_values[:limit] if limit is not None else sorted_values
        total_qty = sum(row["qty"] for row in values)
        total_sales = sum(row["sales"] for row in values)
        total_margin = sum(row["margin"] for row in values)
        total_profitability = (total_margin / total_sales * 100) if total_sales else 0
        result[year] = [
            [
                row["client"],
                format_number(row["qty"]),
                format_number(row["sales"]),
                f"{row['profitability']:.1f}%".replace(".", ","),
            ]
            for row in selected_values
        ]
        result[year].append(
            [
                "Total",
                format_number(total_qty),
                format_number(total_sales),
                f"{total_profitability:.1f}%".replace(".", ","),
                True,
            ]
        )

    return result


def get_regional_summary_by_year(limit: int = 10) -> dict[str, list[list[str | bool]]]:
    result = {year: [] for year in get_dashboard_years()}

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(si.territory, ''), 'No Territory') AS territory,
            SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), COALESCE(NULLIF(si.territory, ''), 'No Territory')
        """,
        as_dict=True,
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = str(row.year)
        sales_amount = flt(row.sales_amount)
        cost_amount = flt(row.cost_amount)
        margin_amount = sales_amount - cost_amount
        grouped[year].append(
            {
                "territory": row.territory,
                "sales": sales_amount,
                "margin": margin_amount,
                "profitability": (margin_amount / sales_amount * 100) if sales_amount else 0,
            }
        )

    for year, values in grouped.items():
        sorted_values = sorted(values, key=lambda row: row["sales"], reverse=True)[:limit]
        total_sales = sum(row["sales"] for row in sorted_values)
        total_margin = sum(row["margin"] for row in sorted_values)
        rows_for_year = [
            [
                row["territory"],
                format_number(row["sales"]),
                format_number(row["margin"]),
                f"{row['profitability']:.1f}%".replace(".", ","),
            ]
            for row in sorted_values
        ]
        rows_for_year.append(
            [
                "Total",
                format_number(total_sales),
                format_number(total_margin),
                f"{(total_margin / total_sales * 100):.1f}%".replace(".", ",") if total_sales else "0,0%",
                True,
            ]
        )
        result[year] = rows_for_year

    return result


def _get_month_value_map(query: str, params: dict[str, Any] | None = None) -> dict[int, float]:
    month_map = _empty_month_map()
    for row in frappe.db.sql(query, params or {}, as_dict=True):
        month_map[row.month_no] = flt(row.value)
    return month_map


def get_avg_cost_chart_data(year: str | None = None) -> dict[str, Any]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year, alias="si")
    month_map = _get_month_value_map(
        f"""
        SELECT
            MONTH(si.posting_date) AS month_no,
            CASE
                WHEN SUM(COALESCE(sii.stock_qty, sii.qty, 0)) = 0 THEN 0
                ELSE SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0))
                    / SUM(COALESCE(sii.stock_qty, sii.qty, 0))
            END AS value
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        {clause}
        GROUP BY MONTH(si.posting_date)
        ORDER BY MONTH(si.posting_date)
        """,
        params,
    )
    return {
        "labels": MONTH_LABELS,
        "datasets": [{"name": f"Сред себ {selected_year}", "values": [round(month_map[i]) for i in range(1, 13)]}],
    }


def get_avg_check_chart_data(year: str | None = None) -> dict[str, Any]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year)
    month_map = _get_month_value_map(
        f"""
        SELECT
            MONTH(posting_date) AS month_no,
            CASE
                WHEN COUNT(name) = 0 THEN 0
                ELSE SUM(COALESCE(base_net_total, net_total, 0)) / COUNT(name)
            END AS value
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        {clause}
        GROUP BY MONTH(posting_date)
        ORDER BY MONTH(posting_date)
        """,
        params,
    )
    return {
        "labels": MONTH_LABELS,
        "datasets": [{"name": f"Сред чек {selected_year}", "values": [round(month_map[i]) for i in range(1, 13)]}],
    }


def get_kg_chart_data(year: str | None = None) -> dict[str, Any]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year, alias="si")
    month_map = _get_month_value_map(
        f"""
        SELECT
            MONTH(si.posting_date) AS month_no,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS value
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        {clause}
        GROUP BY MONTH(si.posting_date)
        ORDER BY MONTH(si.posting_date)
        """,
        params,
    )
    return {
        "labels": MONTH_LABELS,
        "datasets": [{"name": f"КГ {selected_year}", "values": [round(month_map[i]) for i in range(1, 13)]}],
    }


@frappe.whitelist()
def get_sales_total(filters=None):
    return _format_summary_value("sales_total", _resolve_year(filters))


@frappe.whitelist()
def get_cost_total(filters=None):
    return _format_summary_value("cost_total", _resolve_year(filters))


@frappe.whitelist()
def get_margin_total(filters=None):
    return _format_summary_value("margin_total", _resolve_year(filters))


@frappe.whitelist()
def get_rsp_total(filters=None):
    return _format_summary_value("rsp_total", _resolve_year(filters))


@frappe.whitelist()
def get_return_total(filters=None):
    return _format_summary_value("return_total", _resolve_year(filters))


@frappe.whitelist()
def get_kg_total(filters=None):
    return _format_summary_value("kg_total", _resolve_year(filters))


@frappe.whitelist()
def get_avg_check(filters=None):
    return _format_summary_value("avg_check", _resolve_year(filters))
