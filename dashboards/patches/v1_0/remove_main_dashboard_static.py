from __future__ import annotations

import frappe


def execute():
    remove_workspace_link()
    remove_page()


def remove_workspace_link():
    if not frappe.db.exists("Workspace", "Dashboards"):
        return

    workspace = frappe.get_doc("Workspace", "Dashboards")
    original_count = len(workspace.links or [])
    workspace.set(
        "links",
        [
            link
            for link in workspace.links
            if getattr(link, "link_to", None) != "main-dashboard-static"
        ],
    )
    if len(workspace.links or []) != original_count:
        workspace.save(ignore_permissions=True)


def remove_page():
    if frappe.db.exists("Page", "main-dashboard-static"):
        frappe.delete_doc("Page", "main-dashboard-static", ignore_permissions=True, force=True)
