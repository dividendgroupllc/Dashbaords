from __future__ import annotations

import frappe


ACCESS_ROLE = "investor"
DASHBOARD_PAGES = (
    "main-dashboard",
    "page-dashboard",
    "monthly-analysis",
    "overview-dashboard",
    "dividend-analysis",
    "daily-dashboard",
    "supplier-dashboard",
    "sales-dashboard",
    "manufacture-dashboard",
    "comparison-by-weight",
    "comparison-by-amount",
    "comparison-by-product",
    "customer-comparison",
    "product-by-customer",
    "product-comparison",
)
ACCESS_ROLES = (ACCESS_ROLE, "System Manager")


def execute():
    ensure_workspace_roles()
    ensure_page_roles()


def ensure_workspace_roles():
    if not frappe.db.exists("Workspace", "Dashboards"):
        return

    workspace = frappe.get_doc("Workspace", "Dashboards")
    workspace.public = 1
    # Dashboards workspace moduldan ajratilgan (module = NULL): u rol bo'yicha
    # ko'rinadigan oddiy public workspace bo'lishi kerak, modul ruxsatiga bog'liq emas.
    workspace.module = None
    workspace.icon = "chart"
    workspace.parent_page = ""
    workspace.sequence_id = 1.5
    workspace.set("roles", [{"role": role} for role in ACCESS_ROLES])
    workspace.save(ignore_permissions=True)


def ensure_page_roles():
    for page_name in DASHBOARD_PAGES:
        if not frappe.db.exists("Page", page_name):
            continue

        page = frappe.get_doc("Page", page_name)
        page.set("roles", [{"role": role} for role in ACCESS_ROLES])
        page.save(ignore_permissions=True)
