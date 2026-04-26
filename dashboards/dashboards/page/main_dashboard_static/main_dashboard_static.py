from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint, flt, getdate, today

from dashboards.dashboards.dashboard_data import format_number, get_cogs_total, get_rcp_totals


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


def _safe_div(numerator: float, denominator: float) -> float:
    return flt(numerator) / flt(denominator) if flt(denominator) else 0


def _compact_number(value: float, precision: int = 1) -> str:
    absolute = abs(flt(value))
    suffix = ""
    divisor = 1
    if absolute >= 1_000_000_000:
        divisor = 1_000_000_000
        suffix = "B"
    elif absolute >= 1_000_000:
        divisor = 1_000_000
        suffix = "M"
    elif absolute >= 1_000:
        divisor = 1_000
        suffix = "K"

    if suffix:
        compact = flt(value) / divisor
        text = f"{compact:.{precision}f}".rstrip("0").rstrip(".")
        return f"{text}{suffix}"

    return format_number(value, precision=0)


def _format_uzs(value: float) -> str:
    return f"{format_number(value, precision=2)} UZS"


def _format_percent(value: float, precision: int = 1) -> str:
    return f"{flt(value):.{precision}f}%"


def _empty_month_map(default_factory):
    return {month_no: default_factory() for month_no in range(1, 13)}


def _get_dashboard_years() -> list[str]:
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
    years = [str(row.year) for row in rows if row.year]
    if years:
        return years
    return [str(getdate(today()).year)]


def _get_latest_posting_date(year: str) -> Any:
    return frappe.db.sql(
        """
        SELECT MAX(posting_date) AS posting_date
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND YEAR(posting_date) = %(year)s
        """,
        {"year": cint(year)},
        as_dict=True,
    )[0].posting_date


def _resolve_filters(year: str | None = None, month: str | None = None) -> dict[str, Any]:
    years = _get_dashboard_years()
    selected_year = str(year) if year and str(year) in years else years[-1]
    latest_posting_date = _get_latest_posting_date(selected_year)
    default_month = SHORT_MONTHS[getdate(latest_posting_date).month - 1] if latest_posting_date else SHORT_MONTHS[0]
    selected_month = month[:3].title() if month and month[:3].title() in MONTH_INDEX else default_month
    return {
        "years": years,
        "selected_year": selected_year,
        "months": SHORT_MONTHS,
        "selected_month": selected_month,
    }


def _get_period_params(year: str, month: str | None = None) -> dict[str, int]:
    params = {"year": cint(year)}
    month_no = _month_no(month)
    if month_no:
        params["month"] = month_no
    return params


def _period_clause(year: str, month: str | None = None, alias: str = "") -> tuple[str, dict[str, int]]:
    prefix = f"{alias}." if alias else ""
    params = _get_period_params(year, month)
    clause = f" AND YEAR({prefix}posting_date) = %(year)s"
    if "month" in params:
        clause += f" AND MONTH({prefix}posting_date) = %(month)s"
    return clause, params


def _get_monthly_sales_metrics(year: str) -> dict[int, dict[str, float]]:
    clause, params = _period_clause(year)
    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(si.posting_date) AS month_no,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty_total,
            SUM(COALESCE(sii.base_net_amount, sii.net_amount, sii.base_amount, sii.amount, 0)) AS sales_amount,
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
        GROUP BY MONTH(si.posting_date)
        """,
        params,
        as_dict=True,
    )

    month_map = _empty_month_map(lambda: {"qty_total": 0.0, "sales_amount": 0.0, "cost_amount": 0.0, "discount_total": 0.0, "bonus_total": 0.0})
    for row in rows:
        month_map[row.month_no] = {
            "qty_total": flt(row.qty_total),
            "sales_amount": flt(row.sales_amount),
            "cost_amount": flt(row.cost_amount),
            "discount_total": flt(row.discount_total),
            "bonus_total": flt(row.bonus_total),
        }
    return month_map


def _get_monthly_return_metrics(year: str) -> dict[int, dict[str, float]]:
    clause, params = _period_clause(year)
    rows = frappe.db.sql(
        f"""
        SELECT
            MONTH(posting_date) AS month_no,
            SUM(ABS(COALESCE(total_qty, 0))) AS qty_total,
            SUM(ABS(COALESCE(base_net_total, net_total, 0))) AS return_amount,
            SUM(COALESCE(loyalty_amount, 0)) AS loyalty_bonus
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 1
        {clause}
        GROUP BY MONTH(posting_date)
        """,
        params,
        as_dict=True,
    )

    month_map = _empty_month_map(lambda: {"return_qty_total": 0.0, "return_amount": 0.0, "loyalty_bonus": 0.0})
    for row in rows:
        month_map[row.month_no] = {
            "return_qty_total": flt(row.qty_total),
            "return_amount": flt(row.return_amount),
            "loyalty_bonus": flt(row.loyalty_bonus),
        }
    return month_map


def _to_tons(quantity: float) -> float:
    quantity_value = flt(quantity)
    if abs(quantity_value) >= 1000:
        return quantity_value / 1000
    return quantity_value


def _get_sales_volume_data(year: str) -> dict[str, Any]:
    sales_metrics = _get_monthly_sales_metrics(year)
    series = []
    for month_no, month_label in enumerate(SHORT_MONTHS, start=1):
        row = sales_metrics[month_no]
        tons = _to_tons(row["qty_total"])
        amount = flt(row["sales_amount"])
        series.append(
            {
                "month": month_label,
                "tons": round(tons, 2),
                "tons_display": f"{round(tons, 1):g}t" if tons else "",
                "amount": amount,
                "amount_display": _compact_number(amount) if amount else "",
            }
        )
    return {"series": series}


def _get_returns_analysis_data(year: str) -> dict[str, Any]:
    return_metrics = _get_monthly_return_metrics(year)
    series = []
    for month_no, month_label in enumerate(SHORT_MONTHS, start=1):
        row = return_metrics[month_no]
        tons = _to_tons(row["return_qty_total"])
        amount = flt(row["return_amount"])
        series.append(
            {
                "month": month_label,
                "tons": round(tons, 2),
                "tons_display": f"{round(tons, 1):g}t" if tons else "",
                "amount": amount,
                "amount_display": _compact_number(amount) if amount else "",
            }
        )
    return {"series": series}


def _get_profitability_chart_data(year: str) -> dict[str, Any]:
    sales_metrics = _get_monthly_sales_metrics(year)
    return_metrics = _get_monthly_return_metrics(year)
    series = []

    for month_no, month_label in enumerate(SHORT_MONTHS, start=1):
        sales_amount = flt(sales_metrics[month_no]["sales_amount"])
        cost_amount = flt(sales_metrics[month_no]["cost_amount"])
        discount_total = flt(sales_metrics[month_no]["discount_total"])
        return_amount = flt(return_metrics[month_no]["return_amount"])
        rcp_totals = get_rcp_totals(year, month_no)

        margin_amount = sales_amount - cost_amount
        net_profit_amount = margin_amount - discount_total - return_amount - flt(rcp_totals["rcp_total"])
        profitability_percent = _safe_div(net_profit_amount * 100, sales_amount)

        series.append(
            {
                "month": month_label,
                "profit": round(net_profit_amount / 1000, 2),
                "profit_display": f"{round(net_profit_amount / 1000):g}K" if net_profit_amount else "0K",
                "profitability": round(profitability_percent, 2),
                "profitability_display": _format_percent(profitability_percent),
            }
        )

    return {"series": series}


def _get_period_totals(year: str, month: str | None = None) -> dict[str, float]:
    sales_metrics = _get_monthly_sales_metrics(year)
    return_metrics = _get_monthly_return_metrics(year)

    if month:
        month_no = _month_no(month) or 1
        totals = sales_metrics[month_no].copy()
        totals.update(return_metrics[month_no])
    else:
        totals = {
            "qty_total": sum(flt(row["qty_total"]) for row in sales_metrics.values()),
            "sales_amount": sum(flt(row["sales_amount"]) for row in sales_metrics.values()),
            "cost_amount": sum(flt(row["cost_amount"]) for row in sales_metrics.values()),
            "discount_total": sum(flt(row["discount_total"]) for row in sales_metrics.values()),
            "bonus_total": sum(flt(row["bonus_total"]) for row in sales_metrics.values()),
            "return_amount": sum(flt(row["return_amount"]) for row in return_metrics.values()),
            "loyalty_bonus": sum(flt(row["loyalty_bonus"]) for row in return_metrics.values()),
        }

    invoice_clause, invoice_params = _period_clause(year, month)
    invoice_count = frappe.db.sql(
        f"""
        SELECT COUNT(name) AS invoice_count
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        {invoice_clause}
        """,
        invoice_params,
        as_dict=True,
    )[0]

    totals["invoice_count"] = flt(invoice_count.invoice_count)
    return totals


def _get_manufactured_qty(year: str, month: str | None = None) -> float:
    params = {"year": cint(year)}
    month_no = _month_no(month)
    month_clause = ""
    if month_no:
        params["month"] = month_no
        month_clause = " AND MONTH(se.posting_date) = %(month)s"

    row = frappe.db.sql(
        f"""
        SELECT
            SUM(entry_qty) AS manufactured_qty
        FROM (
            SELECT
                se.name,
                CASE
                    WHEN COALESCE(MAX(se.fg_completed_qty), 0) > 0 THEN COALESCE(MAX(se.fg_completed_qty), 0)
                    ELSE SUM(CASE WHEN COALESCE(sed.is_finished_item, 0) = 1 THEN COALESCE(sed.qty, 0) ELSE 0 END)
                END AS entry_qty
            FROM `tabStock Entry` se
            LEFT JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
            WHERE se.docstatus = 1
              AND (se.stock_entry_type = 'Manufacture' OR se.purpose = 'Manufacture')
              AND YEAR(se.posting_date) = %(year)s
              {month_clause}
            GROUP BY se.name
        ) manufacture_entries
        """,
        params,
        as_dict=True,
    )[0]

    return flt(row.manufactured_qty)


def _get_margin_bonus_data(year: str, month: str) -> dict[str, Any]:
    totals = _get_period_totals(year, month)
    margin_value = flt(totals["sales_amount"]) - flt(totals["cost_amount"])
    bonus_value = flt(totals["bonus_total"]) + flt(totals["loyalty_bonus"])
    denominator = margin_value + bonus_value
    margin_percent = round(_safe_div(margin_value * 100, denominator), 1) if denominator else 0
    bonus_percent = round(100 - margin_percent, 1) if denominator else 0
    return {
        "margin_value": margin_value,
        "bonus_value": bonus_value,
        "margin_percent": margin_percent,
        "bonus_percent": bonus_percent,
        "center_value": f"{int(round(margin_percent))}%",
        "center_label": "Margin",
        "margin_display": f"Margin ({margin_percent:g}%)",
        "bonus_display": f"Bonus ({bonus_percent:g}%)",
    }


def _get_previous_period(year: str, month: str) -> tuple[str, str]:
    month_no = _month_no(month) or 1
    if month_no == 1:
        return str(cint(year) - 1), SHORT_MONTHS[-1]
    return year, SHORT_MONTHS[month_no - 2]


def _get_average_check_data(year: str, month: str) -> dict[str, Any]:
    totals = _get_period_totals(year, month)
    current_qty = flt(totals["qty_total"])
    current_cost_amount = flt(totals["cost_amount"]) or flt(get_cogs_total(year, _month_no(month)))
    current_sales_price = _safe_div(totals["sales_amount"], current_qty)
    current_cost_price = _safe_div(current_cost_amount, current_qty)

    previous_year, previous_month = _get_previous_period(year, month)
    previous_totals = _get_period_totals(previous_year, previous_month)
    previous_qty = flt(previous_totals["qty_total"])
    previous_cost_amount = flt(previous_totals["cost_amount"]) or flt(get_cogs_total(previous_year, _month_no(previous_month)))
    previous_sales_price = _safe_div(previous_totals["sales_amount"], previous_qty)
    previous_cost_price = _safe_div(previous_cost_amount, previous_qty)

    sales_change = _safe_div((current_sales_price - previous_sales_price) * 100, previous_sales_price)
    cost_change = _safe_div((current_cost_price - previous_cost_price) * 100, previous_cost_price)

    return {
        "selling_price": current_sales_price,
        "selling_price_display": _format_uzs(current_sales_price),
        "selling_change": sales_change,
        "selling_change_display": _format_percent(sales_change),
        "cost_price": current_cost_price,
        "cost_price_display": _format_uzs(current_cost_price),
        "cost_change": cost_change,
        "cost_change_display": _format_percent(cost_change),
    }


def _get_inventory_breakdown() -> tuple[dict[str, float], dict[str, float]]:
    rows = frappe.db.sql(
        """
        SELECT
            bin.warehouse,
            wh.warehouse_type,
            SUM(COALESCE(bin.stock_value, 0)) AS stock_value
        FROM `tabBin` bin
        INNER JOIN `tabWarehouse` wh ON wh.name = bin.warehouse
        WHERE wh.disabled = 0
          AND wh.is_group = 0
        GROUP BY bin.warehouse, wh.warehouse_type
        HAVING SUM(COALESCE(bin.stock_value, 0)) <> 0
        ORDER BY SUM(COALESCE(bin.stock_value, 0)) DESC
        """,
        as_dict=True,
    )

    stock_rows: dict[str, float] = {}
    wip_rows: dict[str, float] = {}
    for row in rows:
        warehouse_name = str(row.warehouse or "")
        warehouse_type = str(row.warehouse_type or "")
        stock_value = flt(row.stock_value)
        classification_key = f"{warehouse_name} {warehouse_type}".lower()
        if "work in progress" in classification_key or "wip" in classification_key or "hsu" in classification_key:
            wip_rows[warehouse_name] = stock_value
        else:
            stock_rows[warehouse_name] = stock_value

    return stock_rows, wip_rows


def _top_breakdown_rows(rows: dict[str, float], empty_label: str) -> list[list[str]]:
    if not rows:
        return [[empty_label, "0 UZS"], ["Tracked Warehouses", "0"]]

    sorted_rows = sorted(rows.items(), key=lambda item: item[1], reverse=True)
    top_label, top_value = sorted_rows[0]
    return [
        [top_label, _format_uzs(top_value)],
        ["Tracked Warehouses", str(len(sorted_rows))],
    ]


def _get_balance_details_data(year: str, month: str) -> dict[str, Any]:
    stock_rows, wip_rows = _get_inventory_breakdown()
    stock_total = sum(stock_rows.values())
    wip_total = sum(wip_rows.values())

    debt_total = flt(
        frappe.db.sql(
            """
            SELECT SUM(outstanding_amount) AS outstanding_amount
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND COALESCE(is_return, 0) = 0
              AND outstanding_amount > 0
            """,
            as_dict=True,
        )[0].outstanding_amount
        or 0
    )

    period_totals = _get_period_totals(year, month)
    sales_total = flt(period_totals["sales_amount"])
    debt_ratio = _safe_div(debt_total * 100, debt_total + sales_total)
    sales_ratio = 100 - debt_ratio if debt_total + sales_total else 0

    items = [
        {
            "label": "Sklad (Stock)",
            "value": _format_uzs(stock_total),
            "details": _top_breakdown_rows(stock_rows, "No stock warehouse"),
            "open": False,
        },
        {
            "label": "HSU (WIP)",
            "value": _format_uzs(wip_total),
            "details": _top_breakdown_rows(wip_rows, "No WIP warehouse"),
            "open": False,
        },
        {
            "label": "Qarz / Saudo",
            "value": f"{round(debt_ratio):g}% / {round(sales_ratio):g}%",
            "details": [
                ["Debt (Qarz)", _format_percent(debt_ratio, 0)],
                ["Sales (Saudo)", _format_percent(sales_ratio, 0)],
            ],
            "open": True,
        },
    ]

    return {
        "items": items,
        "total_balance": _format_uzs(stock_total + wip_total + debt_total),
        "debt_ratio": debt_ratio,
        "sales_ratio": sales_ratio,
    }


def _get_break_even_data(year: str, month: str) -> dict[str, Any]:
    totals = _get_period_totals(year, month)
    manufactured_qty = _get_manufactured_qty(year, month)
    current_tons = _to_tons(manufactured_qty) or _to_tons(totals["qty_total"])
    sales_amount = flt(totals["sales_amount"])
    cost_amount = flt(totals["cost_amount"])
    return_amount = flt(totals["return_amount"])
    rcp_totals = get_rcp_totals(year, _month_no(month))

    contribution_total = max(sales_amount - cost_amount - return_amount, 0)
    contribution_per_ton = _safe_div(contribution_total, current_tons)
    plan_tons = _safe_div(flt(rcp_totals["rcp_total"]), contribution_per_ton) if contribution_per_ton else 0
    plan_tons = round(plan_tons, 2)
    current_tons = round(current_tons, 2)
    max_tons = max(plan_tons, current_tons, 1)
    plan_ratio = min(_safe_div(plan_tons * 100, max_tons), 100)
    current_ratio = min(_safe_div(current_tons * 100, max_tons), 100)

    debt_total = flt(
        frappe.db.sql(
            """
            SELECT SUM(outstanding_amount) AS outstanding_amount
            FROM `tabSales Invoice`
            WHERE docstatus = 1
              AND COALESCE(is_return, 0) = 0
              AND outstanding_amount > 0
            """,
            as_dict=True,
        )[0].outstanding_amount
        or 0
    )
    debt_vs_sales_total = debt_total + sales_amount
    debt_ratio = _safe_div(debt_total * 100, debt_vs_sales_total)
    sales_ratio = 100 - debt_ratio if debt_vs_sales_total else 0

    return {
        "summary": f"{current_tons:g}t / {plan_tons:g}t",
        "title": "Production Progress",
        "plan_ratio": plan_ratio,
        "current_ratio": current_ratio,
        "start_label": "0t",
        "plan_label": f"Plan: {plan_tons:g}t",
        "current_label": f"Current: {current_tons:g}t",
        "debt_sales_label": f"{round(debt_ratio):g}% / {round(sales_ratio):g}%",
    }


@frappe.whitelist()
def get_dashboard_data(year: str | None = None, month: str | None = None) -> dict[str, Any]:
    filters = _resolve_filters(year, month)
    selected_year = filters["selected_year"]
    selected_month = filters["selected_month"]

    return {
        "filters": filters,
        "sales_volume": _get_sales_volume_data(selected_year),
        "margin_bonus": _get_margin_bonus_data(selected_year, selected_month),
        "average_check": _get_average_check_data(selected_year, selected_month),
        "balance_details": _get_balance_details_data(selected_year, selected_month),
        "break_even": _get_break_even_data(selected_year, selected_month),
        "returns_analysis": _get_returns_analysis_data(selected_year),
        "net_profit_profitability": _get_profitability_chart_data(selected_year),
    }
