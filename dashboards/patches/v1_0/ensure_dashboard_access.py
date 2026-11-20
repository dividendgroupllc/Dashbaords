from __future__ import annotations

import frappe


ACCESS_ROLE = "investor"
DASHBOARD_PAGES = (
    "main-dashboard",
    "investors",
    "page-dashboard",
    "monthly-analysis",
    "overview-dashboard",
    "dividend-analysis",
    "daily-dashboard",
    "supplier-dashboard",
    "sales-dashboard",
    "manufacture-dashboard",
    "cost-price-analysis",
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
    _add_missing_roles(workspace)
    workspace.save(ignore_permissions=True)


def ensure_page_roles():
    for page_name in DASHBOARD_PAGES:
        if not frappe.db.exists("Page", page_name):
            continue

        page = frappe.get_doc("Page", page_name)
        if _add_missing_roles(page):
            page.save(ignore_permissions=True)


def _add_missing_roles(doc) -> bool:
    """ACCESS_ROLES dan yetishmaganini QO'SHADI, borini O'CHIRMAYDI.

    Avval set() bilan butunlay qayta yozilardi — bu after_migrate'da har
    deploy'da boshqa rollarni (masalan salesadmin) o'chirib yuborardi."""
    mavjud = {r.role for r in doc.get("roles", [])}
    ozgardi = False
    for role in ACCESS_ROLES:
        if role not in mavjud:
            doc.append("roles", {"role": role})
            ozgardi = True
    return ozgardi
