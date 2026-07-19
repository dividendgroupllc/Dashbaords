from __future__ import annotations

import json

import frappe


WORKSPACE_NAME = "Dashboards"

HEADER_LABEL = "Все дашборды"
CARD_LABEL = "Дашборды"

SHORTCUT_LABELS_BY_URL = {
    "/app/main-dashboard": "Главный дашборд",
    "/app/investors": "Инвесторы",
    "/app/page-dashboard": "Дашборд",
    "/app/monthly-analysis": "Ежемесячный анализ",
    "/app/overview-dashboard": "Обзорный дашборд",
    "/app/dividend-analysis": "Анализ дивидендов",
    "/app/daily-dashboard": "Ежедневный дашборд",
    "/app/supplier-dashboard": "Дашборд по поставщикам",
    "/app/sales-dashboard": "Дашборд продаж",
    "/app/comparison-by-weight": "Сравнение по весу",
    "/app/comparison-by-amount": "Сравнение по сумме",
    "/app/comparison-by-product": "Сравнение по продуктам",
    "/app/customer-comparison": "Сравнение клиентов",
    "/app/product-by-customer": "Продукты по клиентам",
    "/app/product-comparison": "Сравнение продуктов",
}

LINK_LABELS_BY_ROUTE = {
    route.removeprefix("/app/"): label
    for route, label in SHORTCUT_LABELS_BY_URL.items()
}
WORKSPACE_LINK_ORDER = [
    "main-dashboard",
    "investors",
    "page-dashboard",
    "sales-dashboard",
    "daily-dashboard",
    "supplier-dashboard",
    "monthly-analysis",
    "dividend-analysis",
    "product-comparison",
    "customer-comparison",
    "product-by-customer",
    "comparison-by-weight",
    "comparison-by-amount",
    "comparison-by-product",
]


def execute():
    if not frappe.db.exists("Workspace", WORKSPACE_NAME):
        return

    workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
    update_workspace_placement(workspace)
    update_workspace_content(workspace)
    update_workspace_links(workspace)
    update_workspace_shortcuts(workspace)
    workspace.save(ignore_permissions=True)


def update_workspace_placement(workspace):
    workspace.icon = "chart"
    workspace.parent_page = ""
    workspace.sequence_id = 1.5


def update_workspace_content(workspace):
    if not workspace.content:
        return

    try:
        content = json.loads(workspace.content)
    except ValueError:
        return

    changed = False
    for block in content:
        data = block.get("data") or {}
        if block.get("type") == "card" and block.get("id") == "dashboards_pages":
            data["card_name"] = CARD_LABEL
            changed = True
            continue

        if block.get("type") == "header" and block.get("id") == "dashboards_header":
            data["text"] = f'<span class="h4"><b>{HEADER_LABEL}</b></span>'
            changed = True
            continue

        if block.get("type") != "shortcut":
            continue

        label = get_label_for_shortcut_name(data.get("shortcut_name"))
        if label:
            data["shortcut_name"] = label
            changed = True

    if changed:
        workspace.content = json.dumps(content, ensure_ascii=False, separators=(",", ":"))


def update_workspace_links(workspace):
    card_breaks = [link for link in workspace.links if link.type == "Card Break"]
    links_by_route = {
        link.link_to: link
        for link in workspace.links
        if link.link_type == "Page" and link.link_to in WORKSPACE_LINK_ORDER
    }
    ordered_links = []

    if card_breaks:
        card_breaks[0].label = CARD_LABEL
        card_breaks[0].link_count = len(WORKSPACE_LINK_ORDER)
        ordered_links.append(card_breaks[0])

    for route in WORKSPACE_LINK_ORDER:
        link = links_by_route.get(route)
        if not link:
            continue
        link.label = LINK_LABELS_BY_ROUTE[route]
        ordered_links.append(link)

    if ordered_links:
        workspace.set("links", ordered_links)
        for index, link in enumerate(workspace.links, start=1):
            link.idx = index
        return

    for link in workspace.links:
        if link.link_type == "DocType" and link.type == "Card Break":
            link.label = CARD_LABEL
            continue

        label = LINK_LABELS_BY_ROUTE.get(link.link_to)
        if label:
            link.label = label


def update_workspace_shortcuts(workspace):
    for shortcut in workspace.shortcuts:
        label = SHORTCUT_LABELS_BY_URL.get(shortcut.url)
        if label:
            shortcut.label = label


def get_label_for_shortcut_name(shortcut_name):
    labels_by_english_name = {
        "Main Dashboard": SHORTCUT_LABELS_BY_URL["/app/main-dashboard"],
        "Page Dashboard": SHORTCUT_LABELS_BY_URL["/app/page-dashboard"],
        "Monthly Analysis": SHORTCUT_LABELS_BY_URL["/app/monthly-analysis"],
        "Overview Dashboard": SHORTCUT_LABELS_BY_URL["/app/overview-dashboard"],
        "Dividend Analysis": SHORTCUT_LABELS_BY_URL["/app/dividend-analysis"],
        "Daily Dashboard": SHORTCUT_LABELS_BY_URL["/app/daily-dashboard"],
        "Supplier Dashboard": SHORTCUT_LABELS_BY_URL["/app/supplier-dashboard"],
        "Sales Dashboard": SHORTCUT_LABELS_BY_URL["/app/sales-dashboard"],
        "Comparison by Weight": SHORTCUT_LABELS_BY_URL["/app/comparison-by-weight"],
        "Comparison by Amount": SHORTCUT_LABELS_BY_URL["/app/comparison-by-amount"],
        "Comparison by Product": SHORTCUT_LABELS_BY_URL["/app/comparison-by-product"],
        "Customer Comparison": SHORTCUT_LABELS_BY_URL["/app/customer-comparison"],
        "Product by Customer": SHORTCUT_LABELS_BY_URL["/app/product-by-customer"],
        "Product Comparison": SHORTCUT_LABELS_BY_URL["/app/product-comparison"],
    }

    return labels_by_english_name.get(shortcut_name)
