from __future__ import annotations

import frappe


@frappe.whitelist()
def get_sales_total(filters=None):
    return "15 441 229 885"


@frappe.whitelist()
def get_margin_total(filters=None):
    return "3 488 125 910"


@frappe.whitelist()
def get_margin_minus_discount(filters=None):
    return "3 106 441 338"


@frappe.whitelist()
def get_returns_total(filters=None):
    return "139 221 005"


@frappe.whitelist()
def get_bonus_total(filters=None):
    return "95 008 144"


@frappe.whitelist()
def get_discount_total(filters=None):
    return "381 684 572"
