from __future__ import annotations

import frappe


PAGE_NAME = "manufacture-dashboard"
PAGE_TITLE = "Производственный дашборд"
ACCESS_ROLES = ("investor", "System Manager")


def execute():
    ensure_page()
    ensure_workspace_link()


def ensure_page():
    if frappe.db.exists("Page", PAGE_NAME):
        page = frappe.get_doc("Page", PAGE_NAME)
    else:
        page = frappe.new_doc("Page")
        page.name = PAGE_NAME
        page.page_name = PAGE_NAME

    page.title = PAGE_TITLE
    page.module = "Dashboards"
    page.standard = "Yes"
    page.system_page = 0
    page.set("roles", [{"role": role} for role in ACCESS_ROLES])

    if page.is_new():
        page.insert(ignore_permissions=True)
    else:
        page.save(ignore_permissions=True)


def ensure_workspace_link():
    if not frappe.db.exists("Workspace", "Dashboards"):
        return

    workspace = frappe.get_doc("Workspace", "Dashboards")
    links = list(workspace.links or [])
    if any(getattr(link, "link_to", None) == PAGE_NAME for link in links):
        return

    workspace.append(
        "links",
        {
            "type": "Link",
            "label": PAGE_TITLE,
            "link_type": "Page",
            "link_to": PAGE_NAME,
            "hidden": 0,
            "is_query_report": 0,
            "onboard": 0,
            "link_count": 0,
        },
    )

    for link in workspace.links or []:
        if getattr(link, "type", None) == "Card Break" and getattr(link, "label", None):
            link.link_count = len([row for row in workspace.links or [] if getattr(row, "type", None) == "Link"])
            break

    workspace.save(ignore_permissions=True)
