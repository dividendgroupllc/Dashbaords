from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import flt, getdate, today

from dashboards.dashboards.dashboard_data import (
    MONTH_LABELS,
    convert_company_currency_amount,
    convert_company_currency_amount_like_report,
    convert_to_reporting_currency,
    format_number,
    get_cogs_total,
    get_monthly_sales_from_profit_and_loss,
    get_rcp_totals,
    get_sales_profit_and_loss_period_end,
)


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


def _sum_document_currency_rows(rows: list[dict[str, Any]], amount_field: str) -> float:
    return sum(
        convert_to_reporting_currency(row.get(amount_field), row.get("currency"), row.get("posting_date"), row.get("company"))
        for row in rows
    )


def _sum_company_currency_rows(rows: list[dict[str, Any]], amount_field: str) -> float:
    return sum(
        convert_company_currency_amount(row.get(amount_field), row.get("posting_date"), row.get("company"))
        for row in rows
    )


def get_dashboard_summary(year: str | None = None) -> dict[str, float]:
    invoice_clause, invoice_params = _year_filter_clause(year)
    item_clause, item_params = _year_filter_clause(year, alias="si")
    rcp_totals = get_rcp_totals(year)
    sales_period_end = get_sales_profit_and_loss_period_end(year or get_default_year())

    invoice_totals = frappe.db.sql(
        f"""
        SELECT
            posting_date,
            currency,
            company,
            SUM(CASE WHEN COALESCE(is_return, 0) = 0 THEN COALESCE(net_total, 0) ELSE 0 END) AS sales_total,
            SUM(CASE WHEN COALESCE(is_return, 0) = 1 THEN ABS(COALESCE(net_total, 0)) ELSE 0 END) AS return_total,
            COUNT(CASE WHEN COALESCE(is_return, 0) = 0 THEN name END) AS invoice_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1
        {invoice_clause}
        GROUP BY posting_date, currency, company
        """,
        invoice_params,
        as_dict=True,
    )

    item_totals = frappe.db.sql(
        f"""
        SELECT
            si.posting_date,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS kg_total,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_total
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        {item_clause}
        GROUP BY si.posting_date, si.company
        """,
        item_params,
        as_dict=True,
    )

    sales_total = sum(flt(value) for value in get_monthly_sales_from_profit_and_loss(year or get_default_year()).values())
    cost_total = _sum_company_currency_rows(item_totals, "cost_total") or flt(get_cogs_total(year))
    margin_total = sales_total - cost_total
    invoice_count = sum(flt(row.invoice_count) for row in invoice_totals)
    return_total = sum(
        convert_to_reporting_currency(
            row.get("return_total"),
            row.get("currency"),
            sales_period_end or row.get("posting_date"),
            row.get("company"),
        )
        for row in invoice_totals
    )
    kg_total = sum(flt(row.kg_total) for row in item_totals)

    return {
        "sales_total": sales_total,
        "cost_total": cost_total,
        "margin_total": margin_total,
        "rsp_total": flt(rcp_totals["rcp_total"]),
        "return_total": return_total,
        "kg_total": kg_total,
        "avg_check": sales_total / invoice_count if invoice_count else 0,
    }


def _format_summary_value(key: str, year: str | None = None) -> str:
    return format_number(get_dashboard_summary(year).get(key), precision=0)


def get_sales_by_month(year: str | None = None) -> list[list[str]]:
    selected_year = year or get_default_year()
    month_map = get_monthly_sales_from_profit_and_loss(selected_year)
    return [[MONTH_LABELS[month_no - 1], format_number(month_map[month_no])] for month_no in range(1, 13)]


def get_returns_by_month(year: str | None = None) -> list[list[str]]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year)
    month_map = _empty_month_map()

    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(posting_date) AS month_no,
            posting_date,
            currency,
            company,
            SUM(ABS(COALESCE(net_total, 0))) AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 1
        {clause}
        GROUP BY MONTH(posting_date), posting_date, currency, company
        ORDER BY MONTH(posting_date), posting_date
        """,
        params,
        as_dict=True,
    )

    for row in rows:
        month_map[row.month_no] += convert_to_reporting_currency(row.amount, row.currency, row.posting_date, row.company)

    return [[MONTH_LABELS[month_no - 1], format_number(month_map[month_no])] for month_no in range(1, 13)]


def get_product_margin_by_year(limit: int | None = None) -> dict[str, list[list[str | bool]]]:
    result = {year: [] for year in get_dashboard_years()}

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар') AS item_label,
            si.posting_date,
            si.currency,
            si.company,
            SUM(COALESCE(sii.amount, sii.net_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар'), si.posting_date, si.currency, si.company
        """,
        as_dict=True,
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = str(row.year)
        sales_amount = convert_to_reporting_currency(row.sales_amount, row.currency, row.posting_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        existing = next((item for item in grouped[year] if item["label"] == row.item_label), None)
        if not existing:
            existing = {"label": row.item_label, "sales": 0.0, "margin": 0.0}
            grouped[year].append(existing)
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount

    for year, values in grouped.items():
        sorted_values = sorted(values, key=lambda row: row["margin"], reverse=True)
        top_rows = [
            [
                row["label"],
                format_number(row["margin"]),
                f"{((row['margin'] / row['sales']) * 100) if row['sales'] else 0:.1f}%".replace(".", ","),
            ]
            for row in sorted_values[:limit]
        ]

        total_margin = sum(row["margin"] for row in values)
        total_sales = sum(row["sales"] for row in values)
        total_profitability = (total_margin / total_sales * 100) if total_sales else 0
        top_rows.append(
            ["Итого", format_number(total_margin), f"{total_profitability:.1f}%".replace(".", ","), True]
        )
        result[year] = top_rows

    return result


def get_client_kpi_by_year(limit: int | None = None) -> dict[str, list[list[str | bool]]]:
    result = {year: [] for year in get_dashboard_years()}
    report_end_by_year = {year: get_sales_profit_and_loss_period_end(year) for year in result}

    rows = frappe.db.sql(
        """
        SELECT
            YEAR(si.posting_date) AS year,
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент') AS client,
            si.posting_date,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.base_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент'), si.posting_date, si.company
        """,
        as_dict=True,
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = str(row.year)
        report_end_date = report_end_by_year.get(year) or row.posting_date
        sales_amount = convert_company_currency_amount_like_report(row.sales_amount, report_end_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        existing = next((item for item in grouped[year] if item["client"] == row.client), None)
        if not existing:
            existing = {"client": row.client, "qty": 0.0, "sales": 0.0, "margin": 0.0}
            grouped[year].append(existing)
        existing["qty"] += flt(row.qty_total)
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount

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
                f"{((row['margin'] / row['sales']) * 100) if row['sales'] else 0:.1f}%".replace(".", ","),
            ]
            for row in selected_values
        ]
        result[year].append(
            [
                "Итого",
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
            COALESCE(NULLIF(si.territory, ''), 'Без территории') AS territory,
            si.posting_date,
            si.currency,
            si.company,
            SUM(COALESCE(sii.amount, sii.net_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        GROUP BY YEAR(si.posting_date), COALESCE(NULLIF(si.territory, ''), 'Без территории'), si.posting_date, si.currency, si.company
        """,
        as_dict=True,
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        year = str(row.year)
        sales_amount = convert_to_reporting_currency(row.sales_amount, row.currency, row.posting_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        existing = next((item for item in grouped[year] if item["territory"] == row.territory), None)
        if not existing:
            existing = {"territory": row.territory, "sales": 0.0, "margin": 0.0}
            grouped[year].append(existing)
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount

    for year, values in grouped.items():
        sorted_values = sorted(values, key=lambda row: row["sales"], reverse=True)[:limit]
        total_sales = sum(row["sales"] for row in sorted_values)
        total_margin = sum(row["margin"] for row in sorted_values)
        rows_for_year = [
            [
                row["territory"],
                format_number(row["sales"]),
                format_number(row["margin"]),
                f"{((row['margin'] / row['sales']) * 100) if row['sales'] else 0:.1f}%".replace(".", ","),
            ]
            for row in sorted_values
        ]
        rows_for_year.append(
            [
                "Итого",
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
    qty_map = _get_month_value_map(
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
    month_map = {}
    for month_no in range(1, 13):
        qty_total = flt(qty_map.get(month_no))
        cogs_total = flt(get_cogs_total(selected_year, month_no))
        month_map[month_no] = cogs_total / qty_total if qty_total else 0

    return {
        "labels": MONTH_LABELS,
        "datasets": [{"name": f"Сред себ {selected_year}", "values": [round(month_map[i]) for i in range(1, 13)]}],
    }


def get_avg_check_chart_data(year: str | None = None) -> dict[str, Any]:
    selected_year = year or get_default_year()
    clause, params = _year_filter_clause(selected_year, alias="si")
    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(si.posting_date) AS month_no,
            si.posting_date,
            si.currency,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.amount, sii.net_amount, 0)) AS sales_total
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
        {clause}
        GROUP BY MONTH(si.posting_date), si.posting_date, si.currency, si.company
        ORDER BY MONTH(si.posting_date), si.posting_date
        """,
        params,
        as_dict=True,
    )
    month_totals = {month_no: {"sales": 0.0, "qty": 0.0} for month_no in range(1, 13)}
    for row in rows:
        month_totals[row.month_no]["sales"] += convert_to_reporting_currency(
            row.sales_total, row.currency, row.posting_date, row.company
        )
        month_totals[row.month_no]["qty"] += flt(row.qty_total)
    month_map = {
        month_no: (values["sales"] / values["qty"] if values["qty"] else 0)
        for month_no, values in month_totals.items()
    }
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
