from __future__ import annotations

import frappe

from dashboards.dashboards.dashboard_data import format_number, get_current_month_sales_summary


def _summary_value(key: str) -> str:
    summary = get_current_month_sales_summary()
    precision = 2 if key in {"avg_price", "avg_cost"} else 0
    return format_number(summary.get(key), precision=precision)


@frappe.whitelist()
def get_sales_amount(filters=None):
    return _summary_value("sales_amount")


@frappe.whitelist()
def get_sales_kg(filters=None):
    return _summary_value("sales_kg")


@frappe.whitelist()
def get_cash_total(filters=None):
    return _summary_value("cash_total")


@frappe.whitelist()
def get_bank_total(filters=None):
    return _summary_value("bank_total")


@frappe.whitelist()
def get_collections_total(filters=None):
    return _summary_value("collections_total")


@frappe.whitelist()
def get_debtor_total(filters=None):
    return _summary_value("debtor_total")


@frappe.whitelist()
def get_average_price(filters=None):
    return _summary_value("avg_price")


@frappe.whitelist()
def get_average_cost(filters=None):
    return _summary_value("avg_cost")


@frappe.whitelist()
def get_dividend_total(filters=None):
    return _summary_value("balance_total")
