from __future__ import annotations

import frappe


PAGE_NAME = "investors"
PAGE_TITLE = "Инвесторы"
ANCHOR_PAGE = "main-dashboard"
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
    if any(getattr(link, "link_to", None) == PAGE_NAME for link in workspace.links or []):
        return

    anchor_position = next(
        (
            index
            for index, link in enumerate(workspace.links or [])
            if getattr(link, "link_to", None) == ANCHOR_PAGE
        ),
        None,
    )

    new_link = workspace.append(
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

    # Ссылка должна стоять сразу после «Главного дашборда», а не в конце списка.
    if anchor_position is not None:
        ordered_links = [link for link in workspace.links if link is not new_link]
        ordered_links.insert(anchor_position + 1, new_link)
        workspace.set("links", ordered_links)

    for index, link in enumerate(workspace.links, start=1):
        link.idx = index

    for link in workspace.links:
        if getattr(link, "type", None) == "Card Break" and getattr(link, "label", None):
            link.link_count = len([row for row in workspace.links if getattr(row, "type", None) == "Link"])
            break

    workspace.save(ignore_permissions=True)
