from __future__ import annotations

import frappe


@frappe.whitelist()
def get_sales_total(filters=None):
    return "13 417 391 236"


@frappe.whitelist()
def get_cost_total(filters=None):
    return "10 036 462 087"


@frappe.whitelist()
def get_margin_total(filters=None):
    return "3 380 929 149"


@frappe.whitelist()
def get_rsp_total(filters=None):
    return "1 973 483 300"


@frappe.whitelist()
def get_return_total(filters=None):
    return "129 679 774"


@frappe.whitelist()
def get_kg_total(filters=None):
    return "409 270"


@frappe.whitelist()
def get_avg_check(filters=None):
    return "32 492"
