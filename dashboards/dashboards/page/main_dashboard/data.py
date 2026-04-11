from __future__ import annotations

import frappe


@frappe.whitelist()
def get_sales_amount(filters=None):
    return "(Blank)"


@frappe.whitelist()
def get_sales_kg(filters=None):
    return "(Blank)"


@frappe.whitelist()
def get_cash_total(filters=None):
    return "(Blank)"


@frappe.whitelist()
def get_bank_total(filters=None):
    return "(Blank)"


@frappe.whitelist()
def get_collections_total(filters=None):
    return "(Blank)"


@frappe.whitelist()
def get_debtor_total(filters=None):
    return "1 980 914 578"


@frappe.whitelist()
def get_average_price(filters=None):
    return "0"


@frappe.whitelist()
def get_average_cost(filters=None):
    return "0"


@frappe.whitelist()
def get_dividend_total(filters=None):
    return "($10 926)"
