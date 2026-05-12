from __future__ import annotations

import frappe


RETIRED_PAGES = {"main-dashboard-static", "cash-dashboard", "client-dashboard"}


def execute():
    remove_workspace_links()
    remove_pages()


def remove_workspace_links():
    if not frappe.db.exists("Workspace", "Dashboards"):
        return

    workspace = frappe.get_doc("Workspace", "Dashboards")
    original_count = len(workspace.links or [])
    workspace.set(
        "links",
        [
            link
            for link in workspace.links
            if getattr(link, "link_to", None) not in RETIRED_PAGES
        ],
    )
    if len(workspace.links or []) != original_count:
        workspace.save(ignore_permissions=True)


def remove_pages():
    for page_name in RETIRED_PAGES:
        if frappe.db.exists("Page", page_name):
            frappe.delete_doc("Page", page_name, ignore_permissions=True, force=True)
