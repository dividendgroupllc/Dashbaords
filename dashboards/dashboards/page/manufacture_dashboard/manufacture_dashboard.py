from __future__ import annotations

from functools import lru_cache
from typing import Any

import frappe
from frappe.utils import cint, flt, getdate, now_datetime, today

from dashboards.dashboards.dashboard_data import (
    REPORTING_CURRENCY,
    convert_company_currency_amount,
    format_number,
    get_default_company,
)
from dashboards.dashboards.page.main_dashboard.main_dashboard import (
    _safe_div,
    _to_tons,
)


SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_INDEX = {label: index + 1 for index, label in enumerate(SHORT_MONTHS)}


def get_context(context):
    context.no_cache = 1


def _month_no(month: str | int | None) -> int | None:
    if month in (None, ""):
        return None
    if isinstance(month, int):
        return month if 1 <= month <= 12 else None

    value = str(month).strip()
    if value.isdigit():
        parsed = cint(value)
        return parsed if 1 <= parsed <= 12 else None

    return MONTH_INDEX.get(value[:3].title())


def _format_uzs(value: float, precision: int = 0) -> str:
    return f"{format_number(value, precision=precision)} UZS"


def _format_tons(value: float) -> str:
    return f"{format_number(value, precision=2)} T"


def _empty_month_map() -> dict[int, dict[str, float]]:
    return {
        month_no: {
            "manufactured_qty": 0.0,
            "manufactured_tons": 0.0,
            "manufacturing_cost": 0.0,
            "raw_cost": 0.0,
            "raw_qty": 0.0,
            "cost_per_ton": 0.0,
            "raw_cost_per_qty": 0.0,
        }
        for month_no in range(1, 13)
    }


def _manufacture_condition(alias: str = "se") -> str:
    return f"({alias}.stock_entry_type = 'Manufacture' OR {alias}.purpose = 'Manufacture')"


@lru_cache(maxsize=12)
def _get_monthly_indirect_expense_from_profit_and_loss(year: str) -> dict[int, float]:
    company = get_default_company()
    if not company:
        return {month_no: 0.0 for month_no in range(1, 13)}

    latest_posting_date = frappe.db.sql(
        """
        SELECT MAX(posting_date) AS posting_date
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND YEAR(posting_date) = %(year)s
          AND docstatus = 1
          AND is_cancelled = 0
        """,
        {"company": company, "year": cint(year)},
        as_dict=True,
    )[0].posting_date

    if not latest_posting_date:
        return {month_no: 0.0 for month_no in range(1, 13)}

    from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement
    from erpnext.accounts.utils import get_fiscal_year

    fiscal_year = get_fiscal_year(latest_posting_date, company=company)[0]
    filters = frappe._dict(
        {
            "company": company,
            "from_fiscal_year": fiscal_year,
            "to_fiscal_year": fiscal_year,
            "period_start_date": f"{cint(year)}-01-01",
            "period_end_date": str(getdate(latest_posting_date)),
            "filter_based_on": "Date Range",
            "periodicity": "Monthly",
            "accumulated_values": 0,
            "include_default_book_entries": 1,
            "presentation_currency": REPORTING_CURRENCY,
        }
    )
    columns, data, *_rest = profit_and_loss_statement.execute(filters)

    target_rows = [
        row
        for row in data
        if "Indirect Expenses" in str(row.get("account") or row.get("account_name") or "")
        or "Indirect Expenses" in str(row.get("account_name") or "")
    ]
    target_row = sorted(target_rows, key=lambda row: flt(row.get("indent")))[0] if target_rows else None

    month_map = {month_no: 0.0 for month_no in range(1, 13)}
    if not target_row:
        return month_map

    month_lookup = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    for column in columns:
        fieldname = str(column.get("fieldname") or "")
        if "_" not in fieldname:
            continue
        month_no = month_lookup.get(fieldname.split("_", 1)[0])
        if month_no:
            month_map[month_no] = flt(target_row.get(fieldname))

    return month_map


@lru_cache(maxsize=12)
def _get_dashboard_years() -> list[str]:
    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT YEAR(se.posting_date) AS year
        FROM `tabStock Entry` se
        WHERE se.docstatus = 1
          AND {_manufacture_condition("se")}
          AND se.posting_date IS NOT NULL
        ORDER BY year
        """,
        as_dict=True,
    )
    years = [str(row.year) for row in rows if row.year]
    if years:
        return years
    return [str(getdate(today()).year)]


def _get_latest_posting_date(year: str) -> Any:
    row = frappe.db.sql(
        f"""
        SELECT MAX(se.posting_date) AS posting_date
        FROM `tabStock Entry` se
        WHERE se.docstatus = 1
          AND {_manufacture_condition("se")}
          AND YEAR(se.posting_date) = %(year)s
        """,
        {"year": cint(year)},
        as_dict=True,
    )[0]
    return row.posting_date


def _resolve_filters(year: str | None = None, month: str | None = None) -> dict[str, Any]:
    years = _get_dashboard_years()
    selected_year = str(year) if year and str(year) in years else years[-1]
    latest_posting_date = _get_latest_posting_date(selected_year)
    default_month = SHORT_MONTHS[getdate(latest_posting_date).month - 1] if latest_posting_date else SHORT_MONTHS[0]
    selected_month = month[:3].title() if month and month[:3].title() in MONTH_INDEX else default_month
    return {
        "years": years,
        "months": SHORT_MONTHS,
        "selected_year": selected_year,
        "selected_month": selected_month,
    }


@lru_cache(maxsize=12)
def _get_monthly_manufacture_metrics(year: str) -> dict[int, dict[str, float]]:
    rows = frappe.db.sql(
        f"""
        SELECT
            entry_month,
            posting_date,
            company,
            SUM(manufactured_qty) AS manufactured_qty,
            SUM(raw_cost) AS raw_cost,
            SUM(raw_qty) AS raw_qty,
            SUM(additional_cost) AS additional_cost
        FROM (
            SELECT
                se.name,
                MONTH(se.posting_date) AS entry_month,
                se.posting_date,
                se.company,
                SUM(CASE WHEN COALESCE(sed.is_finished_item, 0) = 1 THEN COALESCE(sed.qty, 0) ELSE 0 END) AS manufactured_qty,
                SUM(CASE WHEN COALESCE(sed.is_finished_item, 0) = 0 THEN ABS(COALESCE(sed.basic_amount, 0)) ELSE 0 END) AS raw_cost,
                SUM(CASE WHEN COALESCE(sed.is_finished_item, 0) = 0 THEN ABS(COALESCE(sed.qty, 0)) ELSE 0 END) AS raw_qty,
                MAX(COALESCE(se.total_additional_costs, 0)) AS additional_cost
            FROM `tabStock Entry` se
            LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
            WHERE se.docstatus = 1
              AND {_manufacture_condition("se")}
              AND YEAR(se.posting_date) = %(year)s
            GROUP BY se.name, MONTH(se.posting_date), se.posting_date, se.company
        ) manufacture_entries
        GROUP BY entry_month, posting_date, company
        """,
        {"year": cint(year)},
        as_dict=True,
    )

    month_map = _empty_month_map()
    for row in rows:
        month_no = cint(row.entry_month)
        if month_no not in month_map:
            continue

        raw_cost = convert_company_currency_amount(row.raw_cost, row.posting_date, row.company)
        additional_cost = convert_company_currency_amount(row.additional_cost, row.posting_date, row.company)
        total_cost = raw_cost + additional_cost
        month_map[month_no]["manufactured_qty"] += flt(row.manufactured_qty)
        month_map[month_no]["manufacturing_cost"] += total_cost
        month_map[month_no]["raw_cost"] += raw_cost
        month_map[month_no]["raw_qty"] += flt(row.raw_qty)

    for month_no, values in month_map.items():
        values["manufactured_tons"] = _to_tons(values["manufactured_qty"])
        values["cost_per_ton"] = _safe_div(values["manufacturing_cost"], values["manufactured_tons"])
        values["raw_cost_per_qty"] = _safe_div(values["raw_cost"], _to_tons(values["raw_qty"]))

    return month_map


@lru_cache(maxsize=24)
def _get_production_table_rows(year: str, month: str | None = None) -> list[dict[str, Any]]:
    month_no = _month_no(month)
    month_clause = "AND MONTH(se.posting_date) = %(month)s" if month_no else ""
    params = {"year": cint(year)}
    if month_no:
        params["month"] = month_no

    rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(sed.item_code, ''), NULLIF(sed.item_name, ''), 'Неизвестный товар') AS item_code,
            COALESCE(NULLIF(sed.item_name, ''), sed.item_code, 'Неизвестный товар') AS item_label,
            se.posting_date,
            se.company,
            SUM(COALESCE(sed.qty, 0)) AS manufactured_qty,
            SUM(
                CASE
                    WHEN COALESCE(sed.amount, 0) != 0 THEN COALESCE(sed.amount, 0)
                    WHEN COALESCE(sed.basic_amount, 0) != 0 THEN COALESCE(sed.basic_amount, 0)
                    ELSE COALESCE(sed.qty, 0) * COALESCE(sed.valuation_rate, 0)
                END
            ) AS manufacturing_amount
        FROM `tabStock Entry` se
        INNER JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
        WHERE se.docstatus = 1
          AND {_manufacture_condition("se")}
          AND COALESCE(sed.is_finished_item, 0) = 1
          AND YEAR(se.posting_date) = %(year)s
          {month_clause}
        GROUP BY
            COALESCE(NULLIF(sed.item_code, ''), NULLIF(sed.item_name, ''), 'Неизвестный товар'),
            COALESCE(NULLIF(sed.item_name, ''), sed.item_code, 'Неизвестный товар'),
            se.posting_date,
            se.company
        """,
        params,
        as_dict=True,
    )

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_key = str(row.item_code or row.item_label or "Неизвестный товар")
        if item_key not in grouped:
            grouped[item_key] = {
                "label": str(row.item_label or item_key),
                "qty": 0.0,
                "summa_seb": 0.0,
            }

        grouped[item_key]["qty"] += flt(row.manufactured_qty)
        grouped[item_key]["summa_seb"] += convert_company_currency_amount(
            row.manufacturing_amount,
            row.posting_date,
            row.company,
        )

    result = []
    for values in grouped.values():
        tons = _to_tons(values["qty"])
        summa_seb = flt(values["summa_seb"])
        result.append(
            {
                "label": values["label"],
                "ton": round(tons, 2),
                "ton_raw": tons,
                "ton_display": _format_tons(tons),
                "summa_seb": round(summa_seb, 2),
                "summa_seb_raw": summa_seb,
                "summa_seb_display": _format_uzs(summa_seb),
            }
        )

    return sorted(result, key=lambda row: (-flt(row["ton"]), row["label"]))


def _add_dop_rasxod_rows(rows: list[dict[str, Any]], indirect_total: float) -> list[dict[str, Any]]:
    month_total_tons = sum(flt(row.get("ton_raw", row.get("ton"))) for row in rows)
    for row in rows:
        dop_rasxod = _safe_div(flt(row.get("ton_raw", row.get("ton"))) * flt(indirect_total), month_total_tons)
        row["dop_rasxod"] = round(dop_rasxod, 2)
        row["dop_rasxod_raw"] = dop_rasxod
        row["dop_rasxod_display"] = _format_uzs(dop_rasxod)
    return rows



def _build_summary(month: str, metrics: dict[int, dict[str, float]]) -> dict[str, Any]:
    month_no = _month_no(month) or 1
    selected_month = metrics[month_no]

    return {
        "monthProduction": round(selected_month["manufactured_tons"], 2),
        "monthProductionDisplay": _format_tons(selected_month["manufactured_tons"]),
        "averageCost": round(selected_month["cost_per_ton"], 2),
        "averageCostDisplay": _format_uzs(selected_month["cost_per_ton"]),
    }


def _build_monthly_series(metrics: dict[int, dict[str, float]]) -> list[dict[str, Any]]:
    series = []
    for month_no, month in enumerate(SHORT_MONTHS, start=1):
        values = metrics[month_no]
        series.append(
            {
                "month": month,
                "ton": round(values["manufactured_tons"], 2),
                "ton_display": _format_tons(values["manufactured_tons"]),
                "cost": round(values["cost_per_ton"], 2),
                "cost_display": _format_uzs(values["cost_per_ton"]),
            }
        )
    return series



@frappe.whitelist()
def get_dashboard_data(year: str | None = None, month: str | None = None) -> dict[str, Any]:
    _get_dashboard_years.cache_clear()
    _get_monthly_indirect_expense_from_profit_and_loss.cache_clear()
    _get_monthly_manufacture_metrics.cache_clear()
    _get_production_table_rows.cache_clear()
    filters = _resolve_filters(year, month)
    selected_year = filters["selected_year"]
    selected_month = filters["selected_month"]
    metrics = _get_monthly_manufacture_metrics(selected_year)
    production_rows = _get_production_table_rows(selected_year, selected_month)
    indirect_total = flt(_get_monthly_indirect_expense_from_profit_and_loss(selected_year).get(_month_no(selected_month) or 0))
    production_rows = _add_dop_rasxod_rows(production_rows, indirect_total)
    summa_seb_total = sum(flt(row.get("summa_seb_raw", row.get("summa_seb"))) for row in production_rows)
    dop_rasxod_total = sum(flt(row.get("dop_rasxod_raw", row.get("dop_rasxod"))) for row in production_rows)
    summary = _build_summary(selected_month, metrics)
    summary.update(
        {
            "summaSebTotal": round(summa_seb_total, 2),
            "summaSebTotalDisplay": _format_uzs(summa_seb_total),
            "dopRasxodTotal": round(dop_rasxod_total, 2),
            "dopRasxodTotalDisplay": _format_uzs(dop_rasxod_total),
        }
    )

    return {
        "filters": filters,
        "summary": summary,
        "monthly": _build_monthly_series(metrics),
        "production_rows": production_rows,
        "updated_at": now_datetime().strftime("%H:%M"),
    }
