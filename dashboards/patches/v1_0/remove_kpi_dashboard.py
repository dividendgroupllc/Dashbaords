from __future__ import annotations

import frappe


KPI_ROUTE = "/app/kpi-dashboard"
KPI_PAGE = "kpi-dashboard"


def execute():
    delete_workspace_shortcuts()
    delete_kpi_number_cards()
    delete_dashboard_kpi_number_cards()
    delete_kpi_page()


def delete_workspace_shortcuts():
    for workspace_name in frappe.get_all("Workspace", pluck="name"):
        workspace = frappe.get_doc("Workspace", workspace_name)
        original_shortcuts = list(workspace.shortcuts or [])
        workspace.shortcuts = [
            shortcut for shortcut in original_shortcuts
            if shortcut.url != KPI_ROUTE and shortcut.link_to != KPI_PAGE
        ]
        if len(workspace.shortcuts) != len(original_shortcuts):
            workspace.save(ignore_permissions=True)


def delete_kpi_number_cards():
    for card_name in frappe.get_all("Number Card", filters={"name": ("like", "KPI Dashboard%")}, pluck="name"):
        frappe.delete_doc("Number Card", card_name, ignore_permissions=True, force=True)


def delete_dashboard_kpi_number_cards():
    for card_name in frappe.get_all("Number Card", filters={"name": ("like", "Dashboard KPI%")}, pluck="name"):
        frappe.delete_doc("Number Card", card_name, ignore_permissions=True, force=True)


def delete_kpi_page():
    if frappe.db.exists("Page", KPI_PAGE):
        frappe.delete_doc("Page", KPI_PAGE, ignore_permissions=True, force=True)
