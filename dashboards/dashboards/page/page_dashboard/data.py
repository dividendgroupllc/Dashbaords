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
    get_item_cogs_map,
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


def _period_start_date(year: str, month: str | None = None):
    if month in MONTH_LABELS:
        month_no = MONTH_LABELS.index(month) + 1
        return getdate(f"{year}-{month_no:02d}-01")

    return getdate(f"{year}-01-01")


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
    rcp_total = flt(rcp_totals["direct_total"])
    margin_total = sales_total - cost_total - rcp_total
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
        "rsp_total": rcp_total,
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


def _get_direct_expense_accounts() -> list[str]:
    root_patterns = ["Direct Expenses", "Direct Expense", "Direct Expence"]
    pattern_conditions = " OR ".join(
        " OR ".join(
            [
                f"root_acc.name = {frappe.db.escape(pattern)}",
                f"root_acc.name LIKE {frappe.db.escape(pattern + ' - %')}",
                f"root_acc.name LIKE {frappe.db.escape('% - ' + pattern + ' - %')}",
                f"root_acc.name LIKE {frappe.db.escape('% - ' + pattern)}",
            ]
        )
        for pattern in root_patterns
    )

    rows = frappe.db.sql(
        f"""
        SELECT acc.name
        FROM `tabAccount` acc
        WHERE acc.disabled = 0
          AND acc.is_group = 0
          AND EXISTS (
              SELECT 1
              FROM `tabAccount` root_acc
              WHERE ({pattern_conditions})
                AND acc.lft >= root_acc.lft
                AND acc.rgt <= root_acc.rgt
          )
        """,
        as_dict=True,
    )
    return [row.name for row in rows]


def _get_direct_expense_total_in_reporting_currency(year: str, month: str | None = None) -> float:
    accounts = _get_direct_expense_accounts()
    if not accounts:
        return flt(get_rcp_totals(year, month)["direct_total"])

    account_filter = ", ".join(frappe.db.escape(account) for account in accounts)
    month_no = MONTH_LABELS.index(month) + 1 if month in MONTH_LABELS else None
    month_filter = f" AND MONTH(gle.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""
    rows = frappe.db.sql(
        f"""
        SELECT
            day_totals.posting_date,
            day_totals.company,
            CASE
                WHEN company.default_currency = 'UZS' THEN day_totals.total
                ELSE day_totals.total * COALESCE(
                    (
                        SELECT ce.exchange_rate
                        FROM `tabCurrency Exchange` ce
                        WHERE ce.from_currency = company.default_currency
                          AND ce.to_currency = 'UZS'
                          AND ce.date <= day_totals.posting_date
                        ORDER BY ce.date DESC
                        LIMIT 1
                    ),
                    (
                        SELECT 1 / ce.exchange_rate
                        FROM `tabCurrency Exchange` ce
                        WHERE ce.from_currency = 'UZS'
                          AND ce.to_currency = company.default_currency
                          AND ce.date <= day_totals.posting_date
                          AND COALESCE(ce.exchange_rate, 0) != 0
                        ORDER BY ce.date DESC
                        LIMIT 1
                    ),
                    1
                )
            END AS total
        FROM (
            SELECT
                gle.posting_date,
                gle.company,
                ABS(IFNULL(SUM(gle.debit - gle.credit), 0)) AS total
            FROM `tabGL Entry` gle
            WHERE gle.docstatus = 1
              AND gle.is_cancelled = 0
              AND gle.account IN ({account_filter})
              AND YEAR(gle.posting_date) = %(year)s
              {month_filter}
            GROUP BY gle.posting_date, gle.company
        ) day_totals
        INNER JOIN `tabCompany` company ON company.name = day_totals.company
        """,
        {"year": int(year)},
        as_dict=True,
    )
    if not rows:
        return flt(get_rcp_totals(year, month)["direct_total"])

    return sum(flt(row.total) for row in rows)


def _get_product_rcp_per_kg(year: str, month: str | None = None) -> float:
    clause, params = _period_clause(year, month, alias="se")
    manufactured_rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(sed.item_code, ''), NULLIF(sed.item_name, ''), 'Неизвестный товар') AS item_code,
            COALESCE(NULLIF(sed.item_name, ''), sed.item_code, 'Неизвестный товар') AS item_label,
            SUM(COALESCE(sed.qty, 0)) AS manufactured_qty
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.docstatus = 1
          AND (se.stock_entry_type = 'Manufacture' OR se.purpose = 'Manufacture')
          AND COALESCE(sed.is_finished_item, 0) = 1
          {clause}
        GROUP BY
            COALESCE(NULLIF(sed.item_code, ''), NULLIF(sed.item_name, ''), 'Неизвестный товар'),
            COALESCE(NULLIF(sed.item_name, ''), sed.item_code, 'Неизвестный товар')
        """,
        params,
        as_dict=True,
    )

    total_manufactured_qty = sum(flt(row.manufactured_qty) for row in manufactured_rows)
    direct_total = _get_direct_expense_total_in_reporting_currency(year, month)
    rcp_per_kg = direct_total / total_manufactured_qty if total_manufactured_qty else 0

    return rcp_per_kg


def get_product_margin_rows(year: str | None = None, month: str | None = None, limit: int | None = None) -> list[list[str | bool]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")
    report_end_date = _period_end_date(selected_year, month)
    rcp_per_kg = _get_product_rcp_per_kg(selected_year, month)
    product_cogs_amounts = get_item_cogs_map(selected_year, month)

    rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Неизвестный товар') AS item_code,
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар') AS item_label,
            si.company,
            SUM(CASE WHEN COALESCE(si.is_return, 0) = 0 THEN COALESCE(sii.stock_qty, sii.qty, 0) ELSE 0 END) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, 0)) AS sales_amount,
            SUM(CASE WHEN COALESCE(si.is_return, 0) = 0 THEN COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0) ELSE 0 END) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          {clause}
        GROUP BY
            COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Неизвестный товар'),
            COALESCE(NULLIF(sii.item_name, ''), sii.item_code, 'Неизвестный товар'),
            si.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in rows:
        sales_amount = convert_company_currency_amount_like_report(row.sales_amount, report_end_date, row.company)
        cost_amount = convert_company_currency_amount_like_report(row.cost_amount, report_end_date, row.company)
        existing = grouped.setdefault(
            row.item_code,
            {
                "label": row.item_label,
                "item_code": row.item_code,
                "qty": 0.0,
                "sales": 0.0,
                "cost": 0.0,
                "rsp": 0.0,
                "margin": 0.0,
                "net_margin": 0.0,
            },
        )
        existing["qty"] += flt(row.qty_total)
        existing["sales"] += sales_amount
        existing["cost"] += cost_amount

    values = list(grouped.values())
    for row in values:
        row["cost"] = product_cogs_amounts.get(
            str(row["label"]),
            product_cogs_amounts.get(str(row.get("item_code") or ""), flt(row["cost"])),
        )
        row["rsp"] = flt(row["qty"]) * rcp_per_kg
        row["margin"] = flt(row["sales"]) - flt(row["cost"])
        row["net_margin"] = flt(row["margin"]) - flt(row["rsp"])

    sorted_values = sorted(values, key=lambda row: row["sales"], reverse=True)
    selected_values = sorted_values[:limit] if limit is not None else sorted_values
    total_qty = sum(flt(row["qty"]) for row in values)
    total_cost = sum(flt(row["cost"]) for row in values)
    total_rsp = sum(flt(row["rsp"]) for row in values)
    total_margin = sum(flt(row["margin"]) for row in values)
    total_net_margin = sum(flt(row["net_margin"]) for row in values)
    total_sales = sum(flt(row["sales"]) for row in values)
    total_profitability = (total_margin / total_sales * 100) if total_sales else 0
    total_rsp_percent = (total_sales / total_rsp * 100) if total_rsp else 0

    result = [
        [
            str(row["label"]),
            format_number(flt(row["qty"]) / 1000, precision=3),
            format_number(row["sales"]),
            format_number(row["cost"]),
            format_number(row["margin"]),
            format_number(row["rsp"]),
            f"{((flt(row['sales']) / flt(row['rsp'])) * 100) if flt(row['rsp']) else 0:.1f}%".replace(".", ","),
            format_number(row["net_margin"]),
            f"{((flt(row['margin']) / flt(row['sales'])) * 100) if flt(row['sales']) else 0:.1f}%".replace(".", ","),
        ]
        for row in selected_values
    ]
    result.append(
        [
            "Итого",
            format_number(total_qty / 1000, precision=3),
            format_number(total_sales),
            format_number(total_cost),
            format_number(total_margin),
            format_number(total_rsp),
            f"{total_rsp_percent:.1f}%".replace(".", ","),
            format_number(total_net_margin),
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


def _get_period_companies(year: str, month: str | None = None) -> list[str]:
    clause, params = _period_clause(year, month)
    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT company
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND company IS NOT NULL
          {clause}
        """,
        params,
        as_dict=True,
    )
    return [row.company for row in rows if row.company]


def _get_report_row_value(row, columns: list[dict[str, Any]], fieldname: str):
    if isinstance(row, dict):
        return row.get(fieldname)

    for index, column in enumerate(columns):
        if column.get("fieldname") == fieldname and index < len(row):
            return row[index]

    return None


def _get_gross_profit_client_rows(year: str, month: str | None = None) -> list[dict[str, Any]]:
    from erpnext.accounts.report.gross_profit.gross_profit import execute as gross_profit_execute

    from_date = _period_start_date(year, month)
    to_date = _period_end_date(year, month)
    result: list[dict[str, Any]] = []

    for company in _get_period_companies(year, month):
        filters = frappe._dict(
            {
                "company": company,
                "from_date": from_date,
                "to_date": to_date,
                "group_by": "Customer",
                "include_returned_invoices": 1,
            }
        )
        columns, rows = gross_profit_execute(filters)
        for row in rows:
            customer = _get_report_row_value(row, columns, "customer")
            if not customer or customer == "Total":
                continue

            customer_name = _get_report_row_value(row, columns, "customer_name") or customer
            selling_amount = _get_report_row_value(row, columns, "selling_amount")
            buying_amount = _get_report_row_value(row, columns, "buying_amount")
            qty = _get_report_row_value(row, columns, "qty")

            result.append(
                {
                    "client": customer_name,
                    "company": company,
                    "sales": convert_company_currency_amount_like_report(selling_amount, to_date, company),
                    "cost": convert_company_currency_amount_like_report(buying_amount, to_date, company),
                    "qty": flt(qty),
                }
            )

    return result


def get_kpi_client_table_rows(year: str | None = None, month: str | None = None) -> list[list[str | bool]]:
    selected_year = year or get_default_year()
    clause, params = _period_clause(selected_year, month, alias="si")
    report_end_date = _period_end_date(selected_year, month)

    bonus_rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент') AS client,
            si.posting_date,
            si.company,
            SUM(
                CASE
                    WHEN COALESCE(si.is_return, 0) = 1 THEN -1
                    ELSE 1
                END * ABS(COALESCE(sii.base_net_amount, sii.base_amount, sii.net_amount, sii.amount, 0))
            ) AS bonus_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND (
              LOWER(TRIM(COALESCE(sii.item_name, ''))) IN ('bonus', 'бонус')
              OR LOWER(TRIM(COALESCE(sii.item_code, ''))) IN ('bonus', 'бонус')
          )
          {clause}
        GROUP BY COALESCE(NULLIF(si.customer_name, ''), si.customer, 'Неизвестный клиент'), si.posting_date, si.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, float | str]] = {}
    for row in _get_gross_profit_client_rows(selected_year, month):
        existing = grouped.setdefault(
            row["client"],
            {
                "client": row["client"],
                "sales": 0.0,
                "cost": 0.0,
                "qty": 0.0,
                "margin": 0.0,
                "bonus": 0.0,
                "discount": 0.0,
                "net_margin": 0.0,
            },
        )
        existing["sales"] += flt(row["sales"])
        existing["cost"] += flt(row["cost"])
        existing["qty"] += flt(row["qty"])

    for row in bonus_rows:
        bonus_amount = convert_company_currency_amount_like_report(row.bonus_amount, report_end_date, row.company)
        existing = grouped.setdefault(
            row.client,
            {
                "client": row.client,
                "sales": 0.0,
                "cost": 0.0,
                "qty": 0.0,
                "margin": 0.0,
                "bonus": 0.0,
                "discount": 0.0,
                "net_margin": 0.0,
            },
        )
        existing["bonus"] += bonus_amount

    values = sorted(grouped.values(), key=lambda row: flt(row["sales"]), reverse=True)
    for row in values:
        row["margin"] = flt(row["sales"]) - flt(row["cost"])

    for row in values:
        row["net_margin"] = flt(row["margin"]) - flt(row["bonus"])

    total_sales = sum(flt(row["sales"]) for row in values)
    total_cost = sum(flt(row["cost"]) for row in values)
    total_qty = sum(flt(row["qty"]) for row in values)
    total_bonus = sum(flt(row["bonus"]) for row in values)
    total_margin = sum(flt(row["margin"]) for row in values)
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
                format_number(margin),
                format_number(row["bonus"]),
                f"{(flt(row['bonus']) / margin * 100) if margin else 0:.1f}%".replace(".", ","),
                format_number(net_margin),
                f"{(margin / sales * 100) if sales else 0:.1f}%".replace(".", ","),
            ]
        )

    result.append(
        [
            "Итого",
            format_number(total_sales),
            format_number(total_cost),
            format_number(total_qty),
            format_number(total_margin),
            format_number(total_bonus),
            f"{(total_bonus / total_margin * 100) if total_margin else 0:.1f}%".replace(".", ","),
            format_number(total_net_margin),
            f"{(total_margin / total_sales * 100) if total_sales else 0:.1f}%".replace(".", ","),
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
            COALESCE(NULLIF(customer.territory, ''), 'Без территории') AS territory,
            si.customer,
            si.posting_date,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.base_amount, 0)) AS sales_amount,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS cost_amount
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        LEFT JOIN `tabCustomer` customer ON customer.name = si.customer
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          {clause}
        GROUP BY COALESCE(NULLIF(customer.territory, ''), 'Без территории'), si.customer, si.posting_date, si.company
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
            {"territory": row.territory, "sales": 0.0, "margin": 0.0, "kg": 0.0, "customers": set()},
        )
        existing["sales"] += sales_amount
        existing["margin"] += sales_amount - cost_amount
        existing["kg"] += flt(row.qty_total)
        if row.customer:
            existing["customers"].add(row.customer)

    result = []
    for territory, values in grouped.items():
        sales = flt(values["sales"])
        kg = flt(values["kg"])
        customer_count = len(values["customers"])
        result.append(
            {
                "territory": territory,
                "sales": sales,
                "margin": flt(values["margin"]),
                "kg": kg,
                "tons": kg / 1000 if kg else 0,
                "akb": customer_count,
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
