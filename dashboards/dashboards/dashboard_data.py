from __future__ import annotations

import calendar
from typing import Any

import frappe
from frappe.utils import cint, flt, format_datetime, get_first_day, get_last_day, getdate, now_datetime, today

REPORTING_CURRENCY = "UZS"

_COMPANY_CURRENCY_CACHE: dict[str, str] = {}
_EXCHANGE_RATE_CACHE: dict[tuple[str, str, str], float] = {}
_DEBTOR_ACCOUNT_CACHE: list[str] | None = None
_CREDITOR_ACCOUNT_CACHE: list[str] | None = None
_SALES_ACCOUNT_CACHE: list[str] | None = None
_STOCK_ACCOUNT_CACHE: list[str] | None = None
_MONTHLY_SALES_PL_CACHE: dict[str, dict[int, float]] = {}
_MONTHLY_NET_PROFIT_PL_CACHE: dict[str, dict[int, float]] = {}
# Memoizes the Profit & Loss report (columns, data) per (company, year) so the sales row
# and the net-profit row are extracted from a single report execution instead of two.
_PL_REPORT_CACHE: dict[tuple[str, str], tuple[list, list]] = {}
_TARGET_DEBTOR_ACCOUNT = "Debtors UZS - P"
_TARGET_STOCK_ACCOUNT = "Склад сырьё - P"
_TARGET_STOCK_ACCOUNT_NUMBER = "1410"
_TARGET_SALES_ACCOUNT = "Sales - P"
_TARGET_COGS_ACCOUNT = "Cost of Goods Sold - P"
_TARGET_FIXED_COST_ROOT_ACCOUNT_NUMBER = "5200"
_TARGET_FIXED_COST_ROOT_ACCOUNT_NAME = "Indirect Expenses"

MONTH_LABELS = [
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]

ENGLISH_MONTH_LABELS = [
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

MONTH_LOOKUP = {
    **{label.lower(): index + 1 for index, label in enumerate(MONTH_LABELS)},
    **{label.lower(): index + 1 for index, label in enumerate(ENGLISH_MONTH_LABELS)},
}


def _get_debtor_account_names() -> list[str]:
    global _DEBTOR_ACCOUNT_CACHE

    if _DEBTOR_ACCOUNT_CACHE is not None:
        return _DEBTOR_ACCOUNT_CACHE

    account_filters = {
        "account_type": "Receivable",
        "disabled": 0,
        "is_group": 0,
    }
    debtor_accounts = frappe.get_all(
        "Account",
        filters={**account_filters, "name": _TARGET_DEBTOR_ACCOUNT},
        pluck="name",
    )

    if not debtor_accounts:
        debtor_accounts = frappe.get_all(
            "Account",
            filters={**account_filters, "account_number": "1311"},
            pluck="name",
        )

    if not debtor_accounts:
        debtor_accounts = frappe.get_all(
            "Account",
            filters=account_filters,
            or_filters=[
                ["Account", "name", "like", "1311 - Debtors%"],
                ["Account", "account_name", "like", "Debtors%"],
            ],
            pluck="name",
        )

    _DEBTOR_ACCOUNT_CACHE = list(dict.fromkeys(debtor_accounts))
    return _DEBTOR_ACCOUNT_CACHE


def get_creditor_account_names() -> list[str]:
    global _CREDITOR_ACCOUNT_CACHE

    if _CREDITOR_ACCOUNT_CACHE is not None:
        return _CREDITOR_ACCOUNT_CACHE

    account_filters = {
        "account_type": "Payable",
        "disabled": 0,
        "is_group": 0,
    }
    creditor_accounts = frappe.get_all(
        "Account",
        filters=account_filters,
        or_filters={
            "account_number": ("like", "2111%"),
            "name": ("like", "2111%"),
        },
        pluck="name",
    )

    if not creditor_accounts:
        creditor_accounts = frappe.get_all(
            "Account",
            filters={
                **account_filters,
                "name": ("like", "Creditors%"),
            },
            pluck="name",
        )

    _CREDITOR_ACCOUNT_CACHE = list(dict.fromkeys(creditor_accounts))
    return _CREDITOR_ACCOUNT_CACHE


def get_sales_account_names() -> list[str]:
    global _SALES_ACCOUNT_CACHE

    if _SALES_ACCOUNT_CACHE is not None:
        return _SALES_ACCOUNT_CACHE

    account_filters = {
        "root_type": "Income",
        "report_type": "Profit and Loss",
        "disabled": 0,
        "is_group": 0,
    }
    sales_accounts = frappe.get_all(
        "Account",
        filters={**account_filters, "name": _TARGET_SALES_ACCOUNT},
        pluck="name",
    )

    if not sales_accounts:
        sales_accounts = frappe.get_all(
            "Account",
            filters={**account_filters, "account_number": "4110"},
            pluck="name",
        )

    if not sales_accounts:
        sales_accounts = frappe.get_all(
            "Account",
            filters=account_filters,
            or_filters=[
                ["Account", "name", "like", "4110%"],
                ["Account", "account_name", "like", "Sales%"],
            ],
            pluck="name",
        )

    _SALES_ACCOUNT_CACHE = list(dict.fromkeys(sales_accounts))
    return _SALES_ACCOUNT_CACHE


def get_cogs_account_names() -> list[str]:
    account_filters = {
        "root_type": "Expense",
        "report_type": "Profit and Loss",
        "disabled": 0,
        "is_group": 0,
    }
    cogs_accounts = frappe.get_all(
        "Account",
        filters={**account_filters, "name": _TARGET_COGS_ACCOUNT},
        pluck="name",
    )

    if not cogs_accounts:
        cogs_accounts = frappe.get_all(
            "Account",
            filters={**account_filters, "account_number": "5111"},
            pluck="name",
        )

    if not cogs_accounts:
        cogs_accounts = frappe.get_all(
            "Account",
            filters=account_filters,
            or_filters=[
                ["Account", "name", "like", "5111%"],
                ["Account", "account_name", "like", "Cost of Goods Sold%"],
            ],
            pluck="name",
        )

    return list(dict.fromkeys(cogs_accounts))


def get_fixed_cost_account_names() -> list[str]:
    account_filters = {
        "root_type": "Expense",
        "report_type": "Profit and Loss",
        "disabled": 0,
    }
    root_account = frappe.db.get_value(
        "Account",
        {**account_filters, "account_number": _TARGET_FIXED_COST_ROOT_ACCOUNT_NUMBER},
        ["lft", "rgt"],
        as_dict=True,
    )

    if not root_account:
        root_candidates = frappe.get_all(
            "Account",
            filters=account_filters,
            or_filters=[
                ["Account", "name", "=", _TARGET_FIXED_COST_ROOT_ACCOUNT_NAME],
                ["Account", "name", "like", f"{_TARGET_FIXED_COST_ROOT_ACCOUNT_NAME} - %"],
                ["Account", "name", "like", f"% - {_TARGET_FIXED_COST_ROOT_ACCOUNT_NAME} - %"],
                ["Account", "name", "like", f"% - {_TARGET_FIXED_COST_ROOT_ACCOUNT_NAME}"],
            ],
            fields=["lft", "rgt"],
            order_by="lft asc",
            limit=1,
        )
        root_account = root_candidates[0] if root_candidates else None

    if root_account:
        fixed_cost_accounts = frappe.get_all(
            "Account",
            filters={
                **account_filters,
                "is_group": 0,
                "lft": (">=", root_account.lft),
                "rgt": ("<=", root_account.rgt),
            },
            pluck="name",
        )
    else:
        fixed_cost_accounts = frappe.get_all(
            "Account",
            filters={
                **account_filters,
                "is_group": 0,
                "account_number": ("like", f"{_TARGET_FIXED_COST_ROOT_ACCOUNT_NUMBER}%"),
            },
            pluck="name",
        )

    return list(dict.fromkeys(fixed_cost_accounts))


def _get_stock_account_names() -> list[str]:
    global _STOCK_ACCOUNT_CACHE

    if _STOCK_ACCOUNT_CACHE is not None:
        return _STOCK_ACCOUNT_CACHE

    account_filters = {
        "root_type": "Asset",
        "disabled": 0,
        "is_group": 0,
    }
    stock_accounts = frappe.get_all(
        "Account",
        filters={**account_filters, "name": _TARGET_STOCK_ACCOUNT},
        pluck="name",
    )

    if not stock_accounts:
        stock_accounts = frappe.get_all(
            "Account",
            filters={**account_filters, "account_number": _TARGET_STOCK_ACCOUNT_NUMBER},
            pluck="name",
        )

    if not stock_accounts:
        stock_accounts = frappe.get_all(
            "Account",
            filters={**account_filters, "account_type": "Stock"},
            pluck="name",
        )

    _STOCK_ACCOUNT_CACHE = list(dict.fromkeys(stock_accounts))
    return _STOCK_ACCOUNT_CACHE


def get_reporting_currency() -> str:
    return REPORTING_CURRENCY


def get_default_company() -> str | None:
    return (
        frappe.defaults.get_user_default("Company")
        or frappe.defaults.get_global_default("company")
        or frappe.db.get_value("Company", {}, "name")
    )


def get_company_currency(company: str | None = None) -> str:
    resolved_company = company or get_default_company()
    if not resolved_company:
        return REPORTING_CURRENCY

    if resolved_company not in _COMPANY_CURRENCY_CACHE:
        _COMPANY_CURRENCY_CACHE[resolved_company] = (
            frappe.db.get_value("Company", resolved_company, "default_currency") or REPORTING_CURRENCY
        )

    return _COMPANY_CURRENCY_CACHE[resolved_company]


def _lookup_currency_exchange_rate(from_currency: str, to_currency: str, transaction_date: Any) -> float:
    normalized_date = str(getdate(transaction_date or today()))
    cache_key = (from_currency, to_currency, normalized_date)
    if cache_key in _EXCHANGE_RATE_CACHE:
        return _EXCHANGE_RATE_CACHE[cache_key]

    if not from_currency or not to_currency or from_currency == to_currency:
        _EXCHANGE_RATE_CACHE[cache_key] = 1.0
        return 1.0

    direct = frappe.get_all(
        "Currency Exchange",
        fields=["exchange_rate"],
        filters={
            "from_currency": from_currency,
            "to_currency": to_currency,
            "date": ("<=", normalized_date),
        },
        order_by="date desc",
        limit=1,
    )
    if direct:
        rate = flt(direct[0].exchange_rate)
        _EXCHANGE_RATE_CACHE[cache_key] = rate
        return rate

    reverse = frappe.get_all(
        "Currency Exchange",
        fields=["exchange_rate"],
        filters={
            "from_currency": to_currency,
            "to_currency": from_currency,
            "date": ("<=", normalized_date),
        },
        order_by="date desc",
        limit=1,
    )
    rate = 1 / flt(reverse[0].exchange_rate) if reverse and flt(reverse[0].exchange_rate) else 0
    _EXCHANGE_RATE_CACHE[cache_key] = rate
    return rate


def convert_to_reporting_currency(
    amount: float | int | None,
    from_currency: str | None,
    transaction_date: Any,
    company: str | None = None,
) -> float:
    value = flt(amount)
    if not value:
        return 0

    source_currency = from_currency or get_company_currency(company)
    if source_currency == REPORTING_CURRENCY:
        return value

    rate = _lookup_currency_exchange_rate(source_currency, REPORTING_CURRENCY, transaction_date)
    return value * rate if rate else value


def convert_company_currency_amount(
    amount: float | int | None,
    transaction_date: Any,
    company: str | None = None,
) -> float:
    return convert_to_reporting_currency(amount, get_company_currency(company), transaction_date, company)


def convert_company_currency_amount_like_report(
    amount: float | int | None,
    transaction_date: Any,
    company: str | None = None,
) -> float:
    value = flt(amount)
    if not value:
        return 0

    company_currency = get_company_currency(company)
    if company_currency == REPORTING_CURRENCY:
        return value

    from erpnext.accounts.report.utils import convert

    return flt(convert(value, REPORTING_CURRENCY, company_currency, getdate(transaction_date or today())))


def _filter_existing_account_names(account_names: list[str]) -> list[str]:
    account_names = [account_name for account_name in account_names if account_name]
    if not account_names:
        return []

    existing_names = set(
        frappe.get_all("Account", filters={"name": ("in", account_names)}, pluck="name")
    )
    return [account_name for account_name in account_names if account_name in existing_names]


def get_gl_account_total(account_name: str, period_end: str | None = None) -> float:
    return get_gl_accounts_total([account_name], period_end=period_end)


def get_gl_accounts_total(account_names: list[str], period_end: str | None = None) -> float:
    account_names = _filter_existing_account_names(account_names)
    if not account_names:
        return 0

    company = frappe.db.get_value("Account", account_names[0], "company") or get_default_company()
    if not company:
        return 0

    to_date = str(getdate(period_end or today()))

    # Closing balance is the cumulative (debit - credit) up to to_date. A single indexed
    # aggregate replaces a full general_ledger report execution that previously rebuilt the
    # whole ledger from 2000-01-01 on every balance card open.
    balance = frappe.db.sql(
        """
        SELECT SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) AS balance
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND account IN %(accounts)s
          AND posting_date <= %(to_date)s
          AND docstatus = 1
          AND is_cancelled = 0
        """,
        {"company": company, "accounts": tuple(account_names), "to_date": to_date},
        as_dict=True,
    )[0].balance

    return convert_company_currency_amount(balance, to_date, company)


def get_stock_total(period_end: str | None = None) -> float:
    return get_gl_accounts_total(_get_stock_account_names(), period_end=period_end)


def get_gl_accounts_period_total(account_names: list[str], from_date: str, to_date: str) -> float:
    account_names = _filter_existing_account_names(account_names)
    if not account_names:
        return 0

    company = frappe.db.get_value("Account", account_names[0], "company") or get_default_company()
    if not company:
        return 0

    from_date = str(getdate(from_date))
    to_date = str(getdate(to_date))

    # Period movement is (credit - debit) over [from_date, to_date] — the report's "Total"
    # row. A single indexed aggregate replaces the full general_ledger report execution.
    total = frappe.db.sql(
        """
        SELECT SUM(COALESCE(credit, 0) - COALESCE(debit, 0)) AS total
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND account IN %(accounts)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          AND is_cancelled = 0
        """,
        {"company": company, "accounts": tuple(account_names), "from_date": from_date, "to_date": to_date},
        as_dict=True,
    )[0].total

    return convert_company_currency_amount(total, to_date, company)


def get_sales_total_for_period(from_date: str, to_date: str) -> float:
    sales_accounts = get_sales_account_names()
    return get_gl_accounts_period_total(sales_accounts, from_date, to_date)


def get_cogs_total_for_period(from_date: str, to_date: str) -> float:
    cogs_accounts = get_cogs_account_names()
    return abs(get_gl_accounts_period_total(cogs_accounts, from_date, to_date))


def get_fixed_cost_total_for_period(from_date: str, to_date: str) -> float:
    fixed_cost_accounts = get_fixed_cost_account_names()
    return abs(get_gl_accounts_period_total(fixed_cost_accounts, from_date, to_date))


def get_expense_category_account_types() -> dict[str, str]:
    """Map every expense account to its ``Expense Category`` type — {account: "Variable"|"Fixed"}.

    A category may point at a group account; its leaf descendants inherit the type. Only
    categories flagged ``is_active`` are read, so a category can be parked without deleting it.
    """
    if not frappe.db.table_exists("Expense Category"):
        return {}

    categories = frappe.get_all(
        "Expense Category",
        filters={"is_active": 1},
        fields=["account", "category_type"],
    )

    account_types: dict[str, str] = {}
    for category in categories:
        category_type = (category.category_type or "").strip().title()
        if not category.account or category_type not in ("Fixed", "Variable"):
            continue

        account = frappe.db.get_value(
            "Account", category.account, ["name", "is_group", "lft", "rgt"], as_dict=True
        )
        if not account:
            continue

        if account.is_group:
            covered_accounts = frappe.get_all(
                "Account",
                filters={"is_group": 0, "lft": (">", account.lft), "rgt": ("<", account.rgt)},
                pluck="name",
            )
        else:
            covered_accounts = [account.name]

        for account_name in covered_accounts:
            account_types[account_name] = category_type

    return account_types


def get_expense_type_totals_for_period(from_date: str, to_date: str) -> dict[str, float]:
    """Split the Харажатлар (indirect expense) period total into variable and fixed buckets.

    Both buckets come strictly from the ``category_type`` of the account's active
    ``Expense Category`` — an account no category covers belongs to neither bucket and is
    reported separately as ``unmapped``. So ``variable + fixed`` is only the categorised part
    of ``get_fixed_cost_total_for_period``, and it grows as the mapping is filled in.
    """
    empty_totals = {"variable": 0.0, "fixed": 0.0, "total": 0.0, "unmapped": 0.0}
    expense_accounts = _filter_existing_account_names(get_fixed_cost_account_names())
    if not expense_accounts:
        return empty_totals

    company = frappe.db.get_value("Account", expense_accounts[0], "company") or get_default_company()
    if not company:
        return empty_totals

    from_date = str(getdate(from_date))
    to_date = str(getdate(to_date))

    rows = frappe.db.sql(
        """
        SELECT account, SUM(COALESCE(credit, 0) - COALESCE(debit, 0)) AS total
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND account IN %(accounts)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          AND is_cancelled = 0
        GROUP BY account
        """,
        {
            "company": company,
            "accounts": tuple(expense_accounts),
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    account_types = get_expense_category_account_types()
    variable_total = 0.0
    fixed_total = 0.0
    unmapped_total = 0.0
    for row in rows:
        amount = convert_company_currency_amount(row.total, to_date, company)
        account_type = account_types.get(row.account)
        if account_type == "Variable":
            variable_total += amount
        elif account_type == "Fixed":
            fixed_total += amount
        else:
            unmapped_total += amount

    variable_value = abs(variable_total)
    fixed_value = abs(fixed_total)
    return {
        "variable": variable_value,
        "fixed": fixed_value,
        "total": variable_value + fixed_value,
        "unmapped": abs(unmapped_total),
    }


def get_sales_profit_and_loss_period_end(year: str | int) -> Any:
    sales_accounts = set(get_sales_account_names())
    company = frappe.db.get_value("Account", next(iter(sales_accounts), None), "company") or get_default_company()
    if not company or not sales_accounts:
        return None

    return frappe.db.sql(
        """
        SELECT MAX(posting_date) AS posting_date
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND account IN %(accounts)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          AND is_cancelled = 0
        """,
        {
            "company": company,
            "accounts": tuple(sales_accounts),
            "from_date": f"{cint(year)}-01-01",
            "to_date": f"{cint(year)}-12-31",
        },
        as_dict=True,
    )[0].posting_date


_PL_MONTH_NO_BY_LABEL = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _map_pl_row_to_months(columns: list, target_row: dict | None) -> dict[int, float]:
    """Spread a Profit & Loss report row's monthly columns into a {1..12: amount} map."""
    month_map = {month_no: 0.0 for month_no in range(1, 13)}
    if not target_row:
        return month_map
    for column in columns:
        fieldname = str(column.get("fieldname") or "")
        if "_" not in fieldname:
            continue
        month_no = _PL_MONTH_NO_BY_LABEL.get(fieldname.split("_", 1)[0])
        if month_no:
            month_map[month_no] = flt(target_row.get(fieldname))
    return month_map


def _get_company_year_period_end(company: str, year: str | int) -> Any:
    """Latest submitted GL posting date for a company within a year (range filter so the
    posting_date index can be used)."""
    return frappe.db.sql(
        """
        SELECT MAX(posting_date) AS posting_date
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND docstatus = 1
          AND is_cancelled = 0
        """,
        {"company": company, "from_date": f"{cint(year)}-01-01", "to_date": f"{cint(year)}-12-31"},
        as_dict=True,
    )[0].posting_date


def _get_profit_and_loss_report(company: str, year: str | int) -> tuple[list, list]:
    """Run the monthly Profit & Loss report once per (company, year) and memoize it.

    The sales card and the net-profit card both read from this single execution. The
    period end is the company's latest posting date for the year, which fully covers the
    sales months (sales entries are GL entries, so the overall max is never earlier)."""
    cache_key = (company, str(year))
    cached = _PL_REPORT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    period_end = _get_company_year_period_end(company, year)
    if not period_end:
        _PL_REPORT_CACHE[cache_key] = ([], [])
        return [], []

    from erpnext.accounts.report.profit_and_loss_statement import profit_and_loss_statement
    from erpnext.accounts.utils import get_fiscal_year

    fiscal_year = get_fiscal_year(period_end, company=company)[0]
    filters = frappe._dict(
        {
            "company": company,
            "from_fiscal_year": fiscal_year,
            "to_fiscal_year": fiscal_year,
            "period_start_date": f"{cint(year)}-01-01",
            "period_end_date": str(getdate(period_end)),
            "filter_based_on": "Date Range",
            "periodicity": "Monthly",
            "accumulated_values": 0,
            "include_default_book_entries": 1,
            "presentation_currency": REPORTING_CURRENCY,
        }
    )
    columns, data, *_rest = profit_and_loss_statement.execute(filters)
    _PL_REPORT_CACHE[cache_key] = (columns, data)
    return columns, data


def get_monthly_sales_from_profit_and_loss(year: str) -> dict[int, float]:
    year_key = str(year)
    if year_key in _MONTHLY_SALES_PL_CACHE:
        return _MONTHLY_SALES_PL_CACHE[year_key]

    sales_accounts = set(get_sales_account_names())
    company = frappe.db.get_value("Account", next(iter(sales_accounts), None), "company") or get_default_company()
    if not company or not sales_accounts:
        month_map = {month_no: 0.0 for month_no in range(1, 13)}
        _MONTHLY_SALES_PL_CACHE[year_key] = month_map
        return month_map

    columns, data = _get_profit_and_loss_report(company, year)

    target_row = None
    for row in data:
        if row.get("account") in sales_accounts:
            target_row = row
            break
        account_name = str(row.get("account_name") or "")
        if any(account_name.startswith(account_name_key.split(" - ", 1)[0]) for account_name_key in sales_accounts):
            target_row = row
            break

    month_map = _map_pl_row_to_months(columns, target_row)
    _MONTHLY_SALES_PL_CACHE[year_key] = month_map
    return month_map


def get_monthly_net_profit_from_profit_and_loss(year: str) -> dict[int, float]:
    year_key = str(year)
    if year_key in _MONTHLY_NET_PROFIT_PL_CACHE:
        return _MONTHLY_NET_PROFIT_PL_CACHE[year_key]

    company = get_default_company()
    if not company:
        month_map = {month_no: 0.0 for month_no in range(1, 13)}
        _MONTHLY_NET_PROFIT_PL_CACHE[year_key] = month_map
        return month_map

    columns, data = _get_profit_and_loss_report(company, year)

    # The report's own "Profit for the year" row is rendered through the session
    # language (e.g. «Прибыль за год» for ru users), so matching it by label breaks
    # for non-English sessions. Compute the same figure from the root account rows
    # instead: their names come straight from tabAccount and are never translated.
    sign_by_root = {
        row.name: 1 if row.root_type == "Income" else -1
        for row in frappe.get_all(
            "Account",
            filters={
                "company": company,
                "parent_account": ("is", "not set"),
                "root_type": ("in", ("Income", "Expense")),
            },
            fields=["name", "root_type"],
        )
    }

    month_map = {month_no: 0.0 for month_no in range(1, 13)}
    for row in data:
        sign = sign_by_root.get(str(row.get("account") or ""))
        if not sign:
            continue
        for month_no, value in _map_pl_row_to_months(columns, row).items():
            month_map[month_no] += sign * value

    _MONTHLY_NET_PROFIT_PL_CACHE[year_key] = month_map
    return month_map


def get_debtor_balance_rows(period_end: str | None = None) -> dict[str, float]:
    debtor_accounts = _get_debtor_account_names()
    if debtor_accounts:
        date_clause = " AND gle.posting_date <= %(period_end)s" if period_end else ""
        params: dict[str, Any] = {"accounts": tuple(debtor_accounts)}
        if period_end:
            params["period_end"] = period_end

        rows = frappe.db.sql(
            f"""
            SELECT
                COALESCE(NULLIF(gle.party, ''), NULLIF(gle.against, ''), gle.account) AS party_label,
                gle.posting_date,
                gle.company,
                SUM(COALESCE(gle.debit, 0) - COALESCE(gle.credit, 0)) AS balance
            FROM `tabGL Entry` gle
            WHERE gle.docstatus = 1
              AND gle.is_cancelled = 0
              AND gle.account IN %(accounts)s
              {date_clause}
            GROUP BY COALESCE(NULLIF(gle.party, ''), NULLIF(gle.against, ''), gle.account), gle.posting_date, gle.company
            ORDER BY party_label ASC
            """,
            params,
            as_dict=True,
        )

        balances_by_party: dict[str, float] = {}
        for row in rows:
            party_label = str(row.party_label or "Unknown")
            balances_by_party[party_label] = balances_by_party.get(party_label, 0) + convert_company_currency_amount(
                row.balance,
                row.posting_date,
                row.company,
            )

        return {
            party_label: balance
            for party_label, balance in balances_by_party.items()
            if flt(balance) > 0
        }

    date_clause = " AND posting_date <= %(period_end)s" if period_end else ""
    params = {"period_end": period_end} if period_end else {}
    rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(customer_name, ''), customer) AS party_label,
            posting_date,
            currency,
            company,
            SUM(COALESCE(outstanding_amount, 0)) AS balance
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND COALESCE(outstanding_amount, 0) > 0
          {date_clause}
        GROUP BY customer, customer_name, posting_date, currency, company
        ORDER BY party_label ASC
        """,
        params,
        as_dict=True,
    )

    balances_by_party: dict[str, float] = {}
    for row in rows:
        party_label = str(row.party_label or "Unknown")
        balances_by_party[party_label] = balances_by_party.get(party_label, 0) + convert_to_reporting_currency(
            row.balance,
            row.currency,
            row.posting_date,
            row.company,
        )

    return {
        party_label: balance
        for party_label, balance in balances_by_party.items()
        if flt(balance) > 0
    }


def get_debtor_total(period_end: str | None = None) -> float:
    debtor_accounts = _get_debtor_account_names()
    if debtor_accounts:
        return get_gl_accounts_total(debtor_accounts, period_end=period_end)

    return sum(get_debtor_balance_rows(period_end=period_end).values())


def get_debtor_daily_balances(year: str | int, month: str | int | None = None) -> dict[int, float]:
    """Running end-of-day debtor balance for each day of the given month.

    Returns ``{day_of_month: balance}`` for every day 1..days_in_month, where each value is the
    cumulative (debit - credit) on the debtor accounts up to and including that day — the same
    closing-balance basis as ``get_debtor_total`` / the «Долг» card. Used to drive the main
    dashboard debt-heatmap calendar.
    """
    month_no = _month_number(month)
    if not year or not month_no:
        return {}

    debtor_accounts = _filter_existing_account_names(_get_debtor_account_names())
    if not debtor_accounts:
        return {}

    company = frappe.db.get_value("Account", debtor_accounts[0], "company") or get_default_company()
    if not company:
        return {}

    first_day = f"{cint(year)}-{month_no:02d}-01"
    last_day = str(get_last_day(first_day))
    days_in_month = calendar.monthrange(cint(year), month_no)[1]
    params = {"company": company, "accounts": tuple(debtor_accounts)}

    # Opening balance carried into the first day of the month (one indexed aggregate).
    opening = frappe.db.sql(
        """
        SELECT SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) AS balance
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND account IN %(accounts)s
          AND posting_date < %(first_day)s
          AND docstatus = 1
          AND is_cancelled = 0
        """,
        {**params, "first_day": first_day},
        as_dict=True,
    )[0].balance

    # Net movement per day within the month (one grouped aggregate).
    daily_rows = frappe.db.sql(
        """
        SELECT DAY(posting_date) AS day_no,
               SUM(COALESCE(debit, 0) - COALESCE(credit, 0)) AS net
        FROM `tabGL Entry`
        WHERE company = %(company)s
          AND account IN %(accounts)s
          AND posting_date BETWEEN %(first_day)s AND %(last_day)s
          AND docstatus = 1
          AND is_cancelled = 0
        GROUP BY DAY(posting_date)
        """,
        {**params, "first_day": first_day, "last_day": last_day},
        as_dict=True,
    )
    daily_flow = {int(row.day_no): flt(row.net) for row in daily_rows if row.day_no}

    balances: dict[int, float] = {}
    running = flt(opening)
    for day in range(1, days_in_month + 1):
        running += daily_flow.get(day, 0.0)
        as_of = f"{cint(year)}-{month_no:02d}-{day:02d}"
        balances[day] = convert_company_currency_amount(running, as_of, company)
    return balances


def get_creditor_total(period_end: str | None = None) -> float:
    creditor_accounts = get_creditor_account_names()
    if creditor_accounts:
        return abs(get_gl_accounts_total(creditor_accounts, period_end=period_end))

    return 0


def _get_cash_account_names() -> list[str]:
    cash_accounts = frappe.get_all(
        "Account",
        filters={
            "root_type": "Asset",
            "account_type": ("in", ["Cash", "Bank"]),
            "disabled": 0,
            "is_group": 0,
        },
        pluck="name",
    )
    return list(dict.fromkeys(cash_accounts))


def get_cash_total(period_end: str | None = None) -> float:
    return get_gl_accounts_total(_get_cash_account_names(), period_end=period_end)


def _month_number(month: str | int | None) -> int | None:
    if month in (None, ""):
        return None

    if isinstance(month, int):
        return month

    month_key = str(month).strip().lower()
    if month_key.isdigit():
        return cint(month_key)

    return MONTH_LOOKUP.get(month_key)


def _period_date_range(year: str | int | None, month: str | int | None = None) -> tuple[str | None, str | None]:
    if not year:
        return None, None

    month_no = _month_number(month)
    if month_no:
        last_day = calendar.monthrange(int(year), month_no)[1]
        return f"{int(year)}-{month_no:02d}-01", f"{int(year)}-{month_no:02d}-{last_day:02d}"

    return f"{int(year)}-01-01", f"{int(year)}-12-31"


def _get_report_row_value(row, columns: list[dict[str, Any]], fieldname: str):
    if isinstance(row, dict):
        return row.get(fieldname)

    for index, column in enumerate(columns):
        if column.get("fieldname") == fieldname and index < len(row):
            return row[index]

    return None


def _get_sales_invoice_companies(from_date: str, to_date: str, invoices: list[str] | None = None) -> list[str]:
    filters: dict[str, Any] = {"from_date": from_date, "to_date": to_date}
    invoice_clause = ""
    if invoices:
        filters["invoices"] = tuple(invoices)
        invoice_clause = " AND name IN %(invoices)s"

    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT company
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          {invoice_clause}
        ORDER BY company
        """,
        filters,
        as_dict=True,
    )
    return [str(row.company) for row in rows if row.company]


def _get_sales_invoice_names(
    from_date: str,
    to_date: str,
    customer: str | None = None,
    day: int | None = None,
) -> list[str]:
    filters: dict[str, Any] = {"from_date": from_date, "to_date": to_date}
    customer_clause = ""
    day_clause = ""

    if customer:
        filters["customer"] = customer
        customer_clause = (
            " AND COALESCE(NULLIF(customer_name, ''), customer, 'Неизвестный клиент') = %(customer)s"
        )

    if day:
        filters["day"] = int(day)
        day_clause = " AND DAY(posting_date) = %(day)s"

    rows = frappe.db.sql(
        f"""
        SELECT name
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date BETWEEN %(from_date)s AND %(to_date)s
          {customer_clause}
          {day_clause}
        ORDER BY posting_date, name
        """,
        filters,
        as_dict=True,
    )
    return [str(row.name) for row in rows if row.name]


def _get_gross_profit_rows_for_company(
    company: str,
    from_date: str,
    to_date: str,
    group_by: str,
    sales_invoice: str | None = None,
) -> tuple[list[dict[str, Any]], list[Any]]:
    from erpnext.accounts.report.gross_profit.gross_profit import execute as gross_profit_execute

    filters = frappe._dict(
        {
            "company": company,
            "from_date": from_date,
            "to_date": to_date,
            "group_by": group_by,
            "include_returned_invoices": 1,
        }
    )
    if sales_invoice:
        filters["sales_invoice"] = sales_invoice

    columns, rows = gross_profit_execute(filters)
    return columns, rows


def get_gross_profit_cost_total(
    year: str | int | None,
    month: str | int | None = None,
    customer: str | None = None,
    day: int | None = None,
) -> float:
    cost_by_item = get_gross_profit_item_cogs_map(year, month, customer=customer, day=day)
    return sum(flt(value) for value in cost_by_item.values())


def get_gross_profit_totals(
    year: str | int | None,
    month: str | int | None = None,
) -> dict[str, float]:
    from_date, to_date = _period_date_range(year, month)
    if not from_date or not to_date:
        return {"selling_amount": 0.0, "buying_amount": 0.0, "gross_profit": 0.0}

    totals = {"selling_amount": 0.0, "buying_amount": 0.0, "gross_profit": 0.0}
    for company in _get_sales_invoice_companies(from_date, to_date):
        columns, rows = _get_gross_profit_rows_for_company(company, from_date, to_date, "Item Code")
        if not rows:
            continue

        total_row = rows[-1]
        if _get_report_row_value(total_row, columns, "item_code") != "Total":
            continue

        for fieldname in totals:
            value = flt(_get_report_row_value(total_row, columns, fieldname))
            totals[fieldname] += convert_company_currency_amount_like_report(value, to_date, company)

    return totals


def get_gross_profit_item_cogs_map(
    year: str | int | None,
    month: str | int | None = None,
    customer: str | None = None,
    day: int | None = None,
) -> dict[str, float]:
    from_date, to_date = _period_date_range(year, month)
    if not from_date or not to_date:
        return {}

    invoices = _get_sales_invoice_names(from_date, to_date, customer=customer, day=day) if customer or day else []
    if (customer or day) and not invoices:
        return {}

    companies = _get_sales_invoice_companies(from_date, to_date, invoices=invoices or None)
    result: dict[str, float] = {}

    if invoices:
        # Batch the invoice -> company lookup instead of one frappe.db.get_value per invoice.
        invoice_companies = {
            row.name: row.company
            for row in frappe.get_all(
                "Sales Invoice", filters={"name": ("in", invoices)}, fields=["name", "company"]
            )
        }
        for invoice in invoices:
            invoice_company = invoice_companies.get(invoice)
            if not invoice_company:
                continue
            columns, rows = _get_gross_profit_rows_for_company(
                str(invoice_company), from_date, to_date, "Item Code", sales_invoice=invoice
            )
            for row in rows:
                item_code = _get_report_row_value(row, columns, "item_code")
                if not item_code or item_code == "Total":
                    continue
                buying_amount = flt(_get_report_row_value(row, columns, "buying_amount"))
                converted_amount = convert_company_currency_amount_like_report(buying_amount, to_date, invoice_company)
                result[str(item_code)] = result.get(str(item_code), 0.0) + converted_amount
        return result

    for company in companies:
        columns, rows = _get_gross_profit_rows_for_company(company, from_date, to_date, "Item Code")
        for row in rows:
            item_code = _get_report_row_value(row, columns, "item_code")
            if not item_code or item_code == "Total":
                continue
            buying_amount = flt(_get_report_row_value(row, columns, "buying_amount"))
            converted_amount = convert_company_currency_amount_like_report(buying_amount, to_date, company)
            result[str(item_code)] = result.get(str(item_code), 0.0) + converted_amount

    return result


def _get_expense_total_by_root(
    year: str | int | None,
    month: str | int | None,
    root_account_patterns: list[str],
    company: str | None = None,
    exclude_account_patterns: list[str] | None = None,
) -> float:
    if not year or not root_account_patterns:
        return 0

    month_no = _month_number(month)
    pattern_conditions = " OR ".join(
        " OR ".join(
            [
                f"root_acc.name = {frappe.db.escape(pattern)}",
                f"root_acc.name LIKE {frappe.db.escape(pattern + ' - %')}",
                f"root_acc.name LIKE {frappe.db.escape('% - ' + pattern + ' - %')}",
                f"root_acc.name LIKE {frappe.db.escape('% - ' + pattern)}",
            ]
        )
        for pattern in root_account_patterns
    )
    exclude_patterns = exclude_account_patterns or []
    exclude_conditions = " OR ".join(
        " OR ".join(
            [
                f"exclude_acc.name = {frappe.db.escape(pattern)}",
                f"exclude_acc.name LIKE {frappe.db.escape(pattern + ' - %')}",
                f"exclude_acc.name LIKE {frappe.db.escape('% - ' + pattern + ' - %')}",
                f"exclude_acc.name LIKE {frappe.db.escape('% - ' + pattern)}",
            ]
        )
        for pattern in exclude_patterns
    )
    exclude_clause = (
        f"""
          AND NOT EXISTS (
              SELECT 1
              FROM `tabAccount` exclude_acc
              WHERE ({exclude_conditions})
                AND acc.lft >= exclude_acc.lft
                AND acc.rgt <= exclude_acc.rgt
          )
        """
        if exclude_conditions
        else ""
    )
    company_filter = f" AND gle.company = {frappe.db.escape(company)}" if company else ""
    month_filter = f" AND MONTH(gle.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""

    rows = frappe.db.sql(
        f"""
        SELECT
            gle.posting_date,
            gle.company,
            IFNULL(SUM(gle.debit - gle.credit), 0) AS total
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.docstatus = 1
          AND gle.is_cancelled = 0
          AND YEAR(gle.posting_date) = {frappe.db.escape(year)}
          {month_filter}
          {company_filter}
          AND EXISTS (
              SELECT 1
              FROM `tabAccount` root_acc
              WHERE ({pattern_conditions})
                AND acc.lft >= root_acc.lft
                AND acc.rgt <= root_acc.rgt
          )
          {exclude_clause}
        GROUP BY gle.posting_date, gle.company
        """,
        as_dict=True,
    )

    # Signed sum (debit - credit) matches the Profit and Loss Statement row for the
    # same subtree; a per-day ABS would flip credit-heavy days and inflate the total.
    return sum(convert_company_currency_amount(row.total, row.posting_date, row.company) for row in rows)


def _get_income_total_by_root(
    year: str | int | None,
    month: str | int | None,
    root_account_patterns: list[str],
    company: str | None = None,
) -> float:
    if not year or not root_account_patterns:
        return 0

    month_no = _month_number(month)
    pattern_conditions = " OR ".join(
        " OR ".join(
            [
                f"root_acc.name = {frappe.db.escape(pattern)}",
                f"root_acc.name LIKE {frappe.db.escape(pattern + ' - %')}",
                f"root_acc.name LIKE {frappe.db.escape('% - ' + pattern + ' - %')}",
                f"root_acc.name LIKE {frappe.db.escape('% - ' + pattern)}",
            ]
        )
        for pattern in root_account_patterns
    )
    company_filter = f" AND gle.company = {frappe.db.escape(company)}" if company else ""
    month_filter = f" AND MONTH(gle.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""

    rows = frappe.db.sql(
        f"""
        SELECT
            gle.posting_date,
            gle.company,
            ABS(IFNULL(SUM(gle.credit - gle.debit), 0)) AS total
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.docstatus = 1
          AND gle.is_cancelled = 0
          AND YEAR(gle.posting_date) = {frappe.db.escape(year)}
          {month_filter}
          {company_filter}
          AND EXISTS (
              SELECT 1
              FROM `tabAccount` root_acc
              WHERE ({pattern_conditions})
                AND acc.lft >= root_acc.lft
                AND acc.rgt <= root_acc.rgt
          )
        GROUP BY gle.posting_date, gle.company
        """,
        as_dict=True,
    )

    return sum(convert_company_currency_amount(row.total, row.posting_date, row.company) for row in rows)


def get_rcp_totals(year: str | int | None, month: str | int | None = None) -> dict[str, float]:
    direct_total = _get_expense_total_by_root(
        year,
        month,
        ["Direct Expenses", "Direct Expense", "Direct Expence"],
        exclude_account_patterns=["Cost of Goods Sold"],
    )
    indirect_total = _get_expense_total_by_root(year, month, ["Indirect Expenses"])
    return {
        "direct_total": direct_total,
        "indirect_total": indirect_total,
        "rcp_total": direct_total + indirect_total,
    }


def get_tax_total(year: str | int | None, month: str | int | None = None) -> float:
    return _get_expense_total_by_root(year, month, ["Duties and Taxes", "Taxes"])


def get_other_income_total(year: str | int | None, month: str | int | None = None) -> float:
    return _get_income_total_by_root(year, month, ["Indirect Income", "Other Income"])


def get_stock_ledger_cost_total(year: str | int | None, month: str | int | None = None) -> float:
    if not year:
        return 0

    month_no = _month_number(month)
    month_filter = f" AND MONTH(sle.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""

    rows = frappe.db.sql(
        f"""
        SELECT
            sle.posting_date,
            sle.company,
            SUM(ABS(COALESCE(sle.stock_value_difference, 0))) AS cost_total
        FROM `tabStock Ledger Entry` sle
        WHERE sle.is_cancelled = 0
          AND sle.voucher_type = 'Sales Invoice'
          AND COALESCE(sle.actual_qty, 0) < 0
          AND YEAR(sle.posting_date) = {frappe.db.escape(year)}
          {month_filter}
        GROUP BY sle.posting_date, sle.company
        """,
        as_dict=True,
    )

    return sum(convert_company_currency_amount(row.cost_total, row.posting_date, row.company) for row in rows)


def get_item_stock_ledger_cost_map(year: str | int | None, month: str | int | None = None) -> dict[str, float]:
    if not year:
        return {}

    month_no = _month_number(month)
    month_filter = f" AND MONTH(sle.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""

    rows = frappe.db.sql(
        f"""
        SELECT
            COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Неизвестный товар') AS item_key,
            sle.posting_date,
            sle.company,
            SUM(ABS(COALESCE(sle.stock_value_difference, 0))) AS cost
        FROM `tabStock Ledger Entry` sle
        INNER JOIN `tabSales Invoice Item` sii ON sii.name = sle.voucher_detail_no
        INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
        WHERE sle.is_cancelled = 0
          AND sle.voucher_type = 'Sales Invoice'
          AND COALESCE(sle.actual_qty, 0) < 0
          AND si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND YEAR(sle.posting_date) = {frappe.db.escape(year)}
          {month_filter}
        GROUP BY COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Неизвестный товар'), sle.posting_date, sle.company
        """,
        as_dict=True,
    )

    result: dict[str, float] = {}
    for row in rows:
        result[row.item_key] = result.get(row.item_key, 0) + convert_company_currency_amount(
            row.cost, row.posting_date, row.company
        )
    return result


def get_cogs_total(year: str | int | None, month: str | int | None = None) -> float:
    return get_gross_profit_cost_total(year, month)


def get_item_cogs_map(year: str | int | None, month: str | int | None = None) -> dict[str, float]:
    return get_gross_profit_item_cogs_map(year, month)


def get_product_rcp_per_kg(year: str | int | None, month: str | int | None = None) -> float:
    if not year:
        return 0

    month_no = _month_number(month)
    month_filter = f" AND MONTH(si.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""

    sold_row = frappe.db.sql(
        f"""
        SELECT SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS qty
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND YEAR(si.posting_date) = {frappe.db.escape(year)}
          {month_filter}
        """,
        as_dict=True,
    )[0]

    total_sold_qty = flt(sold_row.qty)
    if not total_sold_qty:
        return 0

    # РСП ставка = Indirect Expenses (the monthly P&L row) per SOLD kg (сотилган кг,
    # ишлаб чиқарилган эмас); production and sales items are unrelated in the Item
    # master, so the rate is global rather than per item. Шу боис жадвал «RCP сумма»
    # ИТОГО = сотилган кг × ставка = бутун Indirect Expenses (KPI «Сумма РСП» билан тенг).
    return flt(get_rcp_totals(year, month)["indirect_total"]) / total_sold_qty


def get_item_bonus_map(year: str | int | None, month: str | int | None = None) -> dict[str, float]:
    if not year:
        return {}

    month_no = _month_number(month)
    month_filter_sales = f" AND MONTH(si.posting_date) = {frappe.db.escape(month_no)}" if month_no else ""

    rows = frappe.db.sql(
        f"""
        SELECT
            sii.parent AS invoice_name,
            COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Неизвестный товар') AS item_key,
            si.posting_date,
            si.company,
            si.currency,
            SUM(COALESCE(sii.net_amount, sii.amount, sii.base_net_amount, sii.base_amount, 0)) AS item_sales,
            SUM(
                CASE
                    WHEN COALESCE(sii.is_free_item, 0) = 1
                        THEN COALESCE(sii.price_list_rate, 0) * COALESCE(sii.qty, 0)
                    ELSE 0
                END
            ) AS free_bonus
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND YEAR(si.posting_date) = {frappe.db.escape(year)}
          {month_filter_sales}
        GROUP BY sii.parent, COALESCE(NULLIF(sii.item_code, ''), NULLIF(sii.item_name, ''), 'Неизвестный товар'), si.posting_date, si.company, si.currency
        """,
        as_dict=True,
    )

    item_rows: dict[str, list[dict[str, Any]]] = {}
    invoice_totals: dict[str, float] = {}
    invoice_context: dict[str, dict[str, Any]] = {}

    for row in rows:
        invoice_name = str(row.invoice_name or "")
        item_sales = flt(row.item_sales)
        item_rows.setdefault(invoice_name, []).append(
            {
                "item_key": row.item_key,
                "item_sales": item_sales,
                "free_bonus": flt(row.free_bonus),
                "posting_date": row.posting_date,
                "company": row.company,
                "currency": row.currency,
            }
        )
        invoice_totals[invoice_name] = invoice_totals.get(invoice_name, 0) + item_sales
        invoice_context[invoice_name] = {
            "posting_date": row.posting_date,
            "company": row.company,
            "currency": row.currency,
        }

    loyalty_rows = frappe.db.sql(
        f"""
        SELECT
            name AS invoice_name,
            posting_date,
            company,
            currency,
            SUM(COALESCE(loyalty_amount, 0)) AS loyalty_bonus
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND YEAR(posting_date) = {frappe.db.escape(year)}
          {month_filter_sales.replace("si.", "")}
        GROUP BY name, posting_date, company, currency
        """,
        as_dict=True,
    )

    loyalty_by_invoice: dict[str, float] = {}
    for row in loyalty_rows:
        loyalty_by_invoice[str(row.invoice_name or "")] = convert_to_reporting_currency(
            row.loyalty_bonus, row.currency, row.posting_date, row.company
        )

    bonus_map: dict[str, float] = {}
    for invoice_name, items in item_rows.items():
        invoice_total = flt(invoice_totals.get(invoice_name))
        loyalty_bonus = flt(loyalty_by_invoice.get(invoice_name))
        for item in items:
            item_bonus = convert_to_reporting_currency(item["free_bonus"], item["currency"], item["posting_date"], item["company"])
            if invoice_total and loyalty_bonus:
                item_bonus += loyalty_bonus * flt(item["item_sales"]) / invoice_total
            bonus_map[item["item_key"]] = bonus_map.get(item["item_key"], 0) + item_bonus

    return bonus_map


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
            posting_date,
            currency,
            company,
            SUM(COALESCE(net_total, 0)) AS total_amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
        GROUP BY YEAR(posting_date), MONTH(posting_date), posting_date, currency, company
        ORDER BY YEAR(posting_date), MONTH(posting_date), posting_date
        """,
        as_dict=True,
    )

    years = sorted({row.year for row in rows if row.year})
    if year_limit and len(years) > year_limit:
        years = years[-year_limit:]

    monthly_map: dict[tuple[int, int], float] = {}
    for row in rows:
        if row.year not in years:
            continue
        key = (row.year, row.month_no)
        monthly_map[key] = monthly_map.get(key, 0) + convert_to_reporting_currency(
            row.total_amount,
            row.currency,
            row.posting_date,
            row.company,
        )
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
            posting_date,
            currency,
            company,
            SUM(COALESCE(net_total, 0)) AS sales_amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND COALESCE(is_return, 0) = 0
          AND posting_date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY posting_date, currency, company
        """,
        {"start_date": start_date, "end_date": end_date},
        as_dict=True,
    )

    item_totals = frappe.db.sql(
        """
        SELECT
            si.posting_date,
            si.company,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0)) AS sales_kg,
            SUM(COALESCE(sii.stock_qty, sii.qty, 0) * COALESCE(sii.incoming_rate, 0)) AS total_cost
        FROM `tabSales Invoice` si
        INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE si.docstatus = 1
          AND COALESCE(si.is_return, 0) = 0
          AND si.posting_date BETWEEN %(start_date)s AND %(end_date)s
        GROUP BY si.posting_date, si.company
        """,
        {"start_date": start_date, "end_date": end_date},
        as_dict=True,
    )

    money_balances = frappe.db.sql(
        """
        SELECT
            acc.account_type,
            gle.posting_date,
            gle.company,
            SUM(COALESCE(gle.debit, 0) - COALESCE(gle.credit, 0)) AS balance
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` acc ON acc.name = gle.account
        WHERE gle.is_cancelled = 0
          AND acc.is_group = 0
          AND acc.account_type IN ('Cash', 'Bank')
        GROUP BY acc.account_type, gle.posting_date, gle.company
        """,
        as_dict=True,
    )

    collections = frappe.db.sql(
        """
        SELECT
            posting_date,
            company,
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
        GROUP BY posting_date, company
        """,
        {"start_date": start_date, "end_date": end_date},
        as_dict=True,
    )

    balances = {"Cash": 0.0, "Bank": 0.0}
    for row in money_balances:
        balances[row.account_type] = balances.get(row.account_type, 0) + convert_company_currency_amount(
            row.balance,
            row.posting_date,
            row.company,
        )

    sales_kg = sum(flt(row.sales_kg) for row in item_totals)
    sales_amount = sum(
        convert_to_reporting_currency(row.sales_amount, row.currency, row.posting_date, row.company)
        for row in invoice_totals
    )
    total_cost = sum(
        convert_company_currency_amount(row.total_cost, row.posting_date, row.company)
        for row in item_totals
    )
    collections_total = sum(
        convert_company_currency_amount(row.collections_total, row.posting_date, row.company)
        for row in collections
    )
    debtor_amount = get_debtor_total()

    return {
        "sales_amount": sales_amount,
        "sales_kg": sales_kg,
        "cash_total": flt(balances.get("Cash")),
        "bank_total": flt(balances.get("Bank")),
        "collections_total": collections_total,
        "debtor_total": debtor_amount,
        "avg_price": sales_amount / sales_kg if sales_kg else 0,
        "avg_cost": total_cost / sales_kg if sales_kg else 0,
        "balance_total": debtor_amount,
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
    result = [
        frappe._dict(client=party_label, customer=party_label, balance=balance)
        for party_label, balance in get_debtor_balance_rows().items()
    ]
    result.sort(key=lambda row: row["balance"], reverse=True)
    return result[:limit] if limit else result


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
