from __future__ import annotations

import calendar
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


def get_default_period(selected_year: str | None = None) -> tuple[str, str]:
    years = get_dashboard_years()
    year = selected_year if selected_year in years else years[-1]

    latest_row = frappe.db.sql(
        """
        SELECT MAX(posting_date) AS posting_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND YEAR(posting_date) = %(year)s
        """,
        {"year": int(year)},
        as_dict=True,
    )[0]

    if latest_row.posting_date:
        month = MONTH_LABELS[getdate(latest_row.posting_date).month - 1]
    else:
        month = MONTH_LABELS[0]

    return year, month


def _year_filter_clause(year: str | None, alias: str = "") -> tuple[str, dict[str, Any]]:
    prefix = f"{alias}." if alias else ""
    filters: dict[str, Any] = {}
    clause = ""

    if year:
        clause = f" AND YEAR({prefix}posting_date) = %(year)s"
        filters["year"] = int(year)

    return clause, filters


def _period_clause(year: str | None, month: str | None = None, alias: str = "") -> tuple[str, dict[str, Any]]:
    clause, filters = _year_filter_clause(year, alias=alias)
    if month in MONTH_LABELS:
        prefix = f"{alias}." if alias else ""
        clause += f" AND MONTH({prefix}posting_date) = %(month)s"
        filters["month"] = MONTH_LABELS.index(month) + 1
    return clause, filters


def _period_end_date(year: str, month: str | None = None):
    if month in MONTH_LABELS:
        month_no = MONTH_LABELS.index(month) + 1
        last_day = calendar.monthrange(int(year), month_no)[1]
        return getdate(f"{year}-{month_no:02d}-{last_day:02d}")

    return get_sales_profit_and_loss_period_end(year) or getdate(f"{year}-12-31")


def _empty_month_map() -> dict[int, float]:
    return {month_no: 0 for month_no in range(1, 13)}


def _resolve_year(filters=None) -> str:
    if filters:
        parsed_filters = frappe.parse_json(filters) if not isinstance(filters, dict) else filters
        year = parsed_filters.get("year") if parsed_filters else None
        if year:
            return str(year)

    return get_default_year()


def _resolve_period(filters=None) -> tuple[str, str | None]:
    if filters:
        parsed_filters = frappe.parse_json(filters) if not isinstance(filters, dict) else filters
        year = parsed_filters.get("year") if parsed_filters else None
        month = parsed_filters.get("month") if parsed_filters else None
        resolved_year = str(year) if year else get_default_year()
        resolved_month = month if month in MONTH_LABELS else None
        return resolved_year, resolved_month

    return get_default_year(), None


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


def get_dashboard_summary(year: str | None = None, month: str | None = None) -> dict[str, float]:
    selected_year = year or get_default_year()
    invoice_clause, invoice_params = _period_clause(selected_year, month)
    item_clause, item_params = _period_clause(selected_year, month, alias="si")
    rcp_totals = get_rcp_totals(selected_year, month)
    sales_period_end = _period_end_date(selected_year, month)

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

    monthly_sales = get_monthly_sales_from_profit_and_loss(selected_year)
    if month in MONTH_LABELS:
        sales_total = flt(monthly_sales.get(MONTH_LABELS.index(month) + 1))
    else:
        sales_total = sum(flt(value) for value in monthly_sales.values())

    cost_total = _sum_company_currency_rows(item_totals, "cost_total") or flt(get_cogs_total(selected_year, month))
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


def _format_summary_value(key: str, year: str | None = None, month: str | None = None) -> str:
    return format_number(get_dashboard_summary(year, month).get(key), precision=0)


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


def get_product_margin_rows(year: str | None = None, month: str | None = None, limit: int | None = None) -> list[list[str | bool]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")
    report_end_date = _period_end_date(selected_year, month)

    rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар') AS item_label,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.base_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.discount_amount, 0) + COALESCE(sii.distributed_discount_amount, 0)) AS rsp_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          {clause}
        GROUP BY COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар'), si.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in rows:
        sales_amount = convert_company_currency_amount_like_report(row.sales_amount, report_end_date, row.company)
        rsp_amount = convert_company_currency_amount_like_report(row.rsp_amount, report_end_date, row.company)
        cost_amount = convert_company_currency_amount_like_report(row.cost_amount, report_end_date, row.company)
        existing = grouped.setdefault(
            row.item_label,
            {"label": row.item_label, "qty": 0.0, "sales": 0.0, "rsp": 0.0, "margin": 0.0},
        )
        existing["qty"] += flt(row.qty_total)
        existing["sales"] += sales_amount
        existing["rsp"] += rsp_amount
        existing["margin"] += sales_amount - cost_amount

    values = list(grouped.values())
    sorted_values = sorted(values, key=lambda row: row["margin"], reverse=True)
    selected_values = sorted_values[:limit] if limit is not None else sorted_values
    total_qty = sum(flt(row["qty"]) for row in values)
    total_rsp = sum(flt(row["rsp"]) for row in values)
    total_margin = sum(flt(row["margin"]) for row in values)
    total_sales = sum(flt(row["sales"]) for row in values)
    total_profitability = (total_margin / total_sales * 100) if total_sales else 0

    result = [
        [
            str(row["label"]),
            format_number(flt(row["qty"]) / 1000, precision=1),
            format_number(row["sales"]),
            format_number(row["rsp"]),
            format_number(row["margin"]),
            f"{((flt(row['margin']) / flt(row['sales'])) * 100) if flt(row['sales']) else 0:.1f}%".replace(".", ","),
        ]
        for row in selected_values
    ]
    result.append(
        [
            "Итого",
            format_number(total_qty / 1000, precision=1),
            format_number(total_sales),
            format_number(total_rsp),
            format_number(total_margin),
            f"{total_profitability:.1f}%".replace(".", ","),
            True,
        ]
    )
    return result


def get_client_kpi_rows(year: str | None = None, month: str | None = None, limit: int | None = None) -> list[list[str | bool]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")
    report_end_date = _period_end_date(selected_year, month)

    rows = frappe.db.sql(
        f"""
        SELECT
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
          {clause}
        GROUP BY COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент'), si.posting_date, si.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in rows:
        sales_amount = convert_company_currency_amount_like_report(row.sales_amount, report_end_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        existing = grouped.setdefault(row.client, {"client": row.client, "qty": 0.0, "sales": 0.0, "margin": 0.0})
        existing["qty"] += flt(row.qty_total)
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount

    values = list(grouped.values())
    sorted_values = sorted(values, key=lambda row: row["sales"], reverse=True)
    selected_values = sorted_values[:limit] if limit is not None else sorted_values
    total_qty = sum(flt(row["qty"]) for row in values)
    total_sales = sum(flt(row["sales"]) for row in values)
    total_margin = sum(flt(row["margin"]) for row in values)
    total_profitability = (total_margin / total_sales * 100) if total_sales else 0

    result = [
        [
            str(row["client"]),
            format_number(row["qty"]),
            format_number(row["sales"]),
            f"{((flt(row['margin']) / flt(row['sales'])) * 100) if flt(row['sales']) else 0:.1f}%".replace(".", ","),
        ]
        for row in selected_values
    ]
    result.append(
        ["Итого", format_number(total_qty), format_number(total_sales), f"{total_profitability:.1f}%".replace(".", ","), True]
    )
    return result


def get_kpi_client_table_rows(year: str | None = None, month: str | None = None) -> list[list[str | bool]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")
    report_end_date = _period_end_date(selected_year, month)

    sales_rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент') AS client,
            si.posting_date,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.base_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount,
            SUM(COALESCE(sii.discount_amount, 0) + COALESCE(sii.distributed_discount_amount, 0)) AS discount_total,
            SUM(
                CASE
                    WHEN COALESCE(sii.is_free_item, 0) = 1
                        THEN COALESCE(sii.base_price_list_rate, sii.price_list_rate, 0) * COALESCE(sii.qty, 0)
                    ELSE 0
                END
            ) AS bonus_total
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          {clause}
        GROUP BY COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент'), si.posting_date, si.company
        """,
        params,
        as_dict=True,
    )

    return_rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(customer_name, ''), customer, 'Неизвестный клиент') AS client,
            posting_date,
            company,
            SUM(ABS(COALESCE(base_net_total, net_total, 0))) AS return_amount,
            SUM(COALESCE(loyalty_amount, 0)) AS loyalty_bonus
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 1
          {_period_clause(selected_year, month)[0]}
        GROUP BY COALESCE(NULLIF(customer_name, ''), customer, 'Неизвестный клиент'), posting_date, company
        """,
        _period_clause(selected_year, month)[1],
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in sales_rows:
        sales_amount = convert_company_currency_amount_like_report(row.sales_amount, report_end_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        discount_amount = convert_company_currency_amount_like_report(row.discount_total, report_end_date, row.company)
        bonus_amount = convert_company_currency_amount_like_report(row.bonus_total, report_end_date, row.company)
        existing = grouped.setdefault(
            row.client,
            {
                "client": row.client,
                "sales": 0.0,
                "cost": 0.0,
                "qty": 0.0,
                "returns": 0.0,
                "margin": 0.0,
                "bonus": 0.0,
                "discount": 0.0,
                "net_margin": 0.0,
            },
        )
        existing["sales"] += sales_amount
        existing["cost"] += cost_amount
        existing["qty"] += flt(row.qty_total)
        existing["margin"] += sales_amount - cost_amount
        existing["bonus"] += bonus_amount
        existing["discount"] += discount_amount
        existing["net_margin"] += (sales_amount - cost_amount) - discount_amount

    for row in return_rows:
        return_amount = convert_company_currency_amount_like_report(row.return_amount, report_end_date, row.company)
        loyalty_bonus = convert_company_currency_amount_like_report(row.loyalty_bonus, report_end_date, row.company)
        existing = grouped.setdefault(
            row.client,
            {
                "client": row.client,
                "sales": 0.0,
                "cost": 0.0,
                "qty": 0.0,
                "returns": 0.0,
                "margin": 0.0,
                "bonus": 0.0,
                "discount": 0.0,
                "net_margin": 0.0,
            },
        )
        existing["returns"] += return_amount
        existing["bonus"] += loyalty_bonus

    values = sorted(grouped.values(), key=lambda row: flt(row["sales"]), reverse=True)
    total_sales = sum(flt(row["sales"]) for row in values)
    total_cost = sum(flt(row["cost"]) for row in values)
    if values and not total_cost and total_sales:
        period_cogs_total = flt(get_cogs_total(selected_year, month))
        if period_cogs_total:
            for row in values:
                row["cost"] = period_cogs_total * flt(row["sales"]) / total_sales
                row["margin"] = flt(row["sales"]) - flt(row["cost"])
                row["net_margin"] = flt(row["margin"]) - flt(row["discount"])
            total_cost = sum(flt(row["cost"]) for row in values)

    total_qty = sum(flt(row["qty"]) for row in values)
    total_returns = sum(flt(row["returns"]) for row in values)
    total_margin = sum(flt(row["margin"]) for row in values)
    total_bonus = sum(flt(row["bonus"]) for row in values)
    total_discount = sum(flt(row["discount"]) for row in values)
    total_net_margin = sum(flt(row["net_margin"]) for row in values)

    result: list[list[str | bool]] = []
    for row in values:
        sales = flt(row["sales"])
        margin = flt(row["margin"])
        net_margin = flt(row["net_margin"])
        result.append(
            [
                str(row["client"]),
                format_number(sales),
                format_number(row["cost"]),
                format_number(row["qty"]),
                format_number(row["returns"]),
                format_number(margin),
                f"{(margin / sales * 100) if sales else 0:.1f}%".replace(".", ","),
                format_number(row["bonus"]),
                format_number(row["discount"]),
                format_number(net_margin),
                f"{(net_margin / sales * 100) if sales else 0:.1f}%".replace(".", ","),
            ]
        )

    result.append(
        [
            "Итого",
            format_number(total_sales),
            format_number(total_cost),
            format_number(total_qty),
            format_number(total_returns),
            format_number(total_margin),
            f"{(total_margin / total_sales * 100) if total_sales else 0:.1f}%".replace(".", ","),
            format_number(total_bonus),
            format_number(total_discount),
            format_number(total_net_margin),
            f"{(total_net_margin / total_sales * 100) if total_sales else 0:.1f}%".replace(".", ","),
            True,
        ]
    )
    return result


def get_regional_summary_rows(year: str | None = None, month: str | None = None, limit: int = 10) -> list[list[str | bool]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")

    rows = frappe.db.sql(
        f"""
        SELECT
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
          {clause}
        GROUP BY COALESCE(NULLIF(si.territory, ''), 'Без территории'), si.posting_date, si.currency, si.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in rows:
        sales_amount = convert_to_reporting_currency(row.sales_amount, row.currency, row.posting_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        existing = grouped.setdefault(row.territory, {"territory": row.territory, "sales": 0.0, "margin": 0.0})
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount

    values = list(grouped.values())
    sorted_values = sorted(values, key=lambda row: row["sales"], reverse=True)[:limit]
    total_sales = sum(flt(row["sales"]) for row in sorted_values)
    total_margin = sum(flt(row["margin"]) for row in sorted_values)
    result = [
        [
            str(row["territory"]),
            format_number(row["sales"]),
            format_number(row["margin"]),
            f"{((flt(row['margin']) / flt(row['sales'])) * 100) if flt(row['sales']) else 0:.1f}%".replace(".", ","),
        ]
        for row in sorted_values
    ]
    result.append(
        [
            "Итого",
            format_number(total_sales),
            format_number(total_margin),
            f"{(total_margin / total_sales * 100):.1f}%".replace(".", ",") if total_sales else "0,0%",
            True,
        ]
    )
    return result


def get_regional_map_data(year: str | None = None, month: str | None = None) -> list[dict[str, Any]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")
    report_end_date = _period_end_date(selected_year, month)

    rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(si.territory, ''), 'Без территории') AS territory,
            si.posting_date,
            si.company,
            COUNT(DISTINCT si.name) AS invoice_count,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.base_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          {clause}
        GROUP BY COALESCE(NULLIF(si.territory, ''), 'Без территории'), si.posting_date, si.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in rows:
        sales_amount = convert_company_currency_amount_like_report(row.sales_amount, report_end_date, row.company)
        cost_amount = convert_company_currency_amount(row.cost_amount, row.posting_date, row.company)
        existing = grouped.setdefault(
            row.territory,
            {"territory": row.territory, "sales": 0.0, "margin": 0.0, "kg": 0.0, "invoice_count": 0.0},
        )
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount
        existing["kg"] += flt(row.qty_total)
        existing["invoice_count"] += flt(row.invoice_count)

    result = []
    for territory, values in grouped.items():
        sales = flt(values["sales"])
        kg = flt(values["kg"])
        invoice_count = flt(values["invoice_count"])
        result.append(
            {
                "territory": territory,
                "sales": sales,
                "margin": flt(values["margin"]),
                "kg": kg,
                "tons": kg / 1000 if kg else 0,
                "akb": sales / invoice_count if invoice_count else 0,
                "profitability": (flt(values["margin"]) / sales * 100) if sales else 0,
            }
        )

    return sorted(result, key=lambda row: (-flt(row["sales"]), str(row["territory"])))


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
    year, month = _resolve_period(filters)
    return _format_summary_value("sales_total", year, month)


@frappe.whitelist()
def get_cost_total(filters=None):
    year, month = _resolve_period(filters)
    return _format_summary_value("cost_total", year, month)


@frappe.whitelist()
def get_margin_total(filters=None):
    year, month = _resolve_period(filters)
    return _format_summary_value("margin_total", year, month)


@frappe.whitelist()
def get_rsp_total(filters=None):
    year, month = _resolve_period(filters)
    return _format_summary_value("rsp_total", year, month)


@frappe.whitelist()
def get_return_total(filters=None):
    year, month = _resolve_period(filters)
    return _format_summary_value("return_total", year, month)


@frappe.whitelist()
def get_kg_total(filters=None):
    year, month = _resolve_period(filters)
    return _format_summary_value("kg_total", year, month)


@frappe.whitelist()
def get_avg_check(filters=None):
    year, month = _resolve_period(filters)
    return _format_summary_value("avg_check", year, month)
