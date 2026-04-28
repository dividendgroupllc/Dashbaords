from __future__ import annotations

import frappe


DEFAULT_ROUTE_ORDER = [
    "main-dashboard-static",
    "main-dashboard",
    "page-dashboard",
    "kpi-dashboard",
    "daily-dashboard",
    "sales-dashboard",
    "cash-dashboard",
    "client-dashboard",
    "comparison-by-product",
    "dividend-analysis",
    "supplier-dashboard",
    "monthly-analysis",
    "comparison-by-weight",
    "comparison-by-amount",
    "product-comparison",
    "customer-comparison",
    "product-by-customer",
]


@frappe.whitelist()
def get_dashboard_sidebar_items() -> list[dict[str, str]]:
    priority_map = {route: index for index, route in enumerate(DEFAULT_ROUTE_ORDER)}
    pages = frappe.get_all(
        "Page",
        filters={
            "module": "Dashboards",
            "system_page": 0,
        },
        fields=["name", "title"],
        order_by="creation asc",
    )

    pages.sort(key=lambda page: (priority_map.get(page.name, len(priority_map)), page.title or page.name))

    return [
        {
            "label": str(page.title or page.name),
            "route": str(page.name),
        }
        for page in pages
    ]
