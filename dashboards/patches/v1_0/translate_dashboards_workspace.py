from __future__ import annotations

import json

import frappe


WORKSPACE_NAME = "Dashboards"

HEADER_LABEL = "Все дашборды"

SHORTCUT_LABELS_BY_URL = {
    "/app/main-dashboard": "Главный дашборд",
    "/app/monthly-analysis": "Ежемесячный анализ",
    "/app/overview-dashboard": "Обзорный дашборд",
    "/app/dividend-analysis": "Анализ дивидендов",
    "/app/daily-dashboard": "Ежедневный дашборд",
    "/app/cash-dashboard": "Дашборд по кассе",
    "/app/client-dashboard": "Дашборд по клиентам",
    "/app/supplier-dashboard": "Дашборд по поставщикам",
    "/app/sales-dashboard": "Дашборд продаж",
    "/app/comparison-by-weight": "Сравнение по весу",
    "/app/comparison-by-amount": "Сравнение по сумме",
    "/app/comparison-by-product": "Сравнение по продуктам",
    "/app/customer-comparison": "Сравнение клиентов",
    "/app/product-by-customer": "Продукты по клиентам",
    "/app/product-comparison": "Сравнение продуктов",
}


def execute():
    if not frappe.db.exists("Workspace", WORKSPACE_NAME):
        return

    workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)
    update_workspace_content(workspace)
    update_workspace_shortcuts(workspace)
    workspace.save(ignore_permissions=True)


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


def update_workspace_shortcuts(workspace):
    for shortcut in workspace.shortcuts:
        label = SHORTCUT_LABELS_BY_URL.get(shortcut.url)
        if label:
            shortcut.label = label


def get_label_for_shortcut_name(shortcut_name):
    labels_by_english_name = {
        "Main Dashboard": SHORTCUT_LABELS_BY_URL["/app/main-dashboard"],
        "Monthly Analysis": SHORTCUT_LABELS_BY_URL["/app/monthly-analysis"],
        "Overview Dashboard": SHORTCUT_LABELS_BY_URL["/app/overview-dashboard"],
        "Dividend Analysis": SHORTCUT_LABELS_BY_URL["/app/dividend-analysis"],
        "Daily Dashboard": SHORTCUT_LABELS_BY_URL["/app/daily-dashboard"],
        "Cash Dashboard": SHORTCUT_LABELS_BY_URL["/app/cash-dashboard"],
        "Client Dashboard": SHORTCUT_LABELS_BY_URL["/app/client-dashboard"],
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
