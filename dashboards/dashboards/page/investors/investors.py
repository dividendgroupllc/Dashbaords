from __future__ import annotations

from functools import lru_cache
from typing import Any

import frappe
from frappe.utils import flt, getdate, now_datetime, today

from dashboards.dashboards.cache import dashboard_cache
from dashboards.dashboards.dashboard_data import (
    _period_date_range,
    convert_company_currency_amount,
    format_number,
    get_default_company,
    get_monthly_net_profit_from_profit_and_loss,
)


SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_INDEX = {label: index + 1 for index, label in enumerate(SHORT_MONTHS)}
RU_MONTH_FULL = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}

# Доли инвесторов в чистой прибыли; выплаты читаются из GL по счетам Dividends Paid-N.
INVESTORS = (
    {"key": "investor_1", "label": "М.М.+А.Ф", "share": 0.82, "account_name": "Dividends Paid-1"},
    {"key": "investor_2", "label": "Н.С.", "share": 0.10, "account_name": "Dividends Paid-2"},
    {"key": "investor_3", "label": "Одил", "share": 0.08, "account_name": "Dividends Paid-3"},
)


def get_context(context):
    context.no_cache = 1


def _format_uzs(value: float) -> str:
    return f"{format_number(value)} UZS"


def _month_no(month: str | None) -> int | None:
    if not month:
        return None
    return MONTH_INDEX.get(str(month)[:3].title())


@lru_cache(maxsize=1)
def _resolve_dividend_accounts() -> tuple[tuple[str, tuple[str, ...]], ...]:
    resolved = []
    for investor in INVESTORS:
        accounts = frappe.get_all(
            "Account",
            filters={"account_name": investor["account_name"], "is_group": 0},
            pluck="name",
        )
        if not accounts:
            accounts = frappe.get_all(
                "Account",
                filters={"name": ("like", f"{investor['account_name']}%"), "is_group": 0},
                pluck="name",
            )
        resolved.append((investor["key"], tuple(accounts)))
    return tuple(resolved)


@lru_cache(maxsize=1)
def _get_dashboard_years() -> tuple[str, ...]:
    rows = frappe.db.sql(
        """
        SELECT DISTINCT YEAR(posting_date) AS year
        FROM `tabGL Entry`
        WHERE docstatus = 1
          AND is_cancelled = 0
          AND posting_date IS NOT NULL
        ORDER BY year
        """,
        as_dict=True,
    )
    years = tuple(str(row.year) for row in rows if row.year)
    return years or (str(getdate(today()).year),)


def _resolve_filters(year: str | None = None, month: str | None = None) -> dict[str, Any]:
    years = list(_get_dashboard_years())
    selected_year = str(year) if year and str(year) in years else years[-1]
    # По умолчанию выбран текущий месяц; month="all" — явный годовой режим
    # (повторный клик по активному месяцу в UI снимает выбор).
    default_month = SHORT_MONTHS[getdate(today()).month - 1]
    if month:
        value = str(month).strip()
        if value.lower() in ("all", "year"):
            selected_month = ""
        else:
            month_key = value[:3].title()
            selected_month = month_key if month_key in MONTH_INDEX else default_month
    else:
        selected_month = default_month
    return {
        "years": years,
        "months": SHORT_MONTHS,
        "selected_year": selected_year,
        "selected_month": selected_month,
    }


def _resolve_net_profit(selected_year: str, selected_month: str) -> float:
    month_map = get_monthly_net_profit_from_profit_and_loss(selected_year)
    month_no = _month_no(selected_month)
    if month_no:
        return flt(month_map.get(month_no))
    return flt(sum(month_map.values()))


def _get_period_payouts(selected_year: str, selected_month: str) -> dict[str, float]:
    payouts = {investor["key"]: 0.0 for investor in INVESTORS}
    from_date, to_date = _period_date_range(selected_year, _month_no(selected_month))
    if not from_date:
        return payouts

    account_map: dict[str, str] = {}
    for key, accounts in _resolve_dividend_accounts():
        for account in accounts:
            account_map[account] = key
    if not account_map:
        return payouts

    company = get_default_company()
    company_clause = "AND company = %(company)s" if company else ""
    rows = frappe.db.sql(
        f"""
        SELECT account, SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) AS paid
        FROM `tabGL Entry`
        WHERE account IN %(accounts)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          AND is_cancelled = 0
          {company_clause}
        GROUP BY account
        """,
        {
            "accounts": tuple(account_map),
            "from_date": from_date,
            "to_date": to_date,
            "company": company,
        },
        as_dict=True,
    )
    for row in rows:
        key = account_map.get(str(row.account))
        if key:
            payouts[key] += convert_company_currency_amount(row.paid, to_date, company)
    return payouts


def _build_period_label(selected_year: str, selected_month: str) -> str:
    month_no = _month_no(selected_month)
    if month_no:
        return f"{RU_MONTH_FULL[month_no]} {selected_year}"
    return f"{selected_year} · весь год"


@frappe.whitelist()
@dashboard_cache("investors")
def get_dashboard_data(year: str | None = None, month: str | None = None) -> dict[str, Any]:
    _get_dashboard_years.cache_clear()
    _resolve_dividend_accounts.cache_clear()

    filters = _resolve_filters(year, month)
    selected_year = filters["selected_year"]
    selected_month = filters["selected_month"]

    net_profit = _resolve_net_profit(selected_year, selected_month)
    payouts = _get_period_payouts(selected_year, selected_month)

    investor_rows = []
    total_due = total_received = 0.0
    for investor in INVESTORS:
        due = net_profit * investor["share"]
        received = flt(payouts.get(investor["key"]))
        remaining = due - received
        received_pct = None
        if due > 0:
            received_pct = round(max(0.0, min(100.0, received / due * 100)), 1)
        investor_rows.append(
            {
                "key": investor["key"],
                "label": investor["label"],
                "share_pct": round(investor["share"] * 100, 2),
                "share_pct_display": f"{format_number(investor['share'] * 100)}%",
                "due": round(due, 2),
                "due_display": _format_uzs(due),
                "received": round(received, 2),
                "received_display": _format_uzs(received),
                "remaining": round(remaining, 2),
                "remaining_display": _format_uzs(remaining),
                "received_pct": received_pct,
                "is_overdrawn": remaining < 0,
            }
        )
        total_due += due
        total_received += received

    total_remaining = total_due - total_received
    return {
        "filters": filters,
        "period_label": _build_period_label(selected_year, selected_month),
        "summary": {
            "net_profit": round(net_profit, 2),
            "net_profit_display": _format_uzs(net_profit),
            "received_total": round(total_received, 2),
            "received_total_display": _format_uzs(total_received),
            "remaining_total": round(total_remaining, 2),
            "remaining_total_display": _format_uzs(total_remaining),
        },
        "investors": investor_rows,
        "totals": {
            "share_pct_display": "100%",
            "due": round(total_due, 2),
            "due_display": _format_uzs(total_due),
            "received": round(total_received, 2),
            "received_display": _format_uzs(total_received),
            "remaining": round(total_remaining, 2),
            "remaining_display": _format_uzs(total_remaining),
        },
        "updated_at": now_datetime().strftime("%H:%M"),
    }
