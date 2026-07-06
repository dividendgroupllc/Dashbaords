from __future__ import annotations

import frappe


DEFAULT_ROUTE_ORDER = [
    "main-dashboard",
    "page-dashboard",
    "daily-dashboard",
    "sales-dashboard",
    "manufacture-dashboard",
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
DEFAULT_ROUTE_LABELS = {
    "main-dashboard": "Главный дашборд",
    "page-dashboard": "Дашборд",
    "daily-dashboard": "Ежедневный дашборд",
    "sales-dashboard": "Дашборд продаж",
    "manufacture-dashboard": "Производственный дашборд",
    "comparison-by-product": "Сравнение по продуктам",
    "dividend-analysis": "Анализ дивидендов",
    "supplier-dashboard": "Дашборд по поставщикам",
    "monthly-analysis": "Ежемесячный анализ",
    "comparison-by-weight": "Сравнение по весу",
    "comparison-by-amount": "Сравнение по сумме",
    "product-comparison": "Сравнение продуктов",
    "customer-comparison": "Сравнение клиентов",
    "product-by-customer": "Продукты по клиентам",
}
HIDDEN_ROUTES = {"kpi-dashboard"}


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

    page_map = {str(page.name): str(page.title or page.name) for page in pages if page.name not in HIDDEN_ROUTES}
    route_names = [route for route in DEFAULT_ROUTE_ORDER if route not in HIDDEN_ROUTES]
    route_names.extend(
        str(page.name)
        for page in sorted(pages, key=lambda page: (priority_map.get(page.name, len(priority_map)), page.title or page.name))
        if page.name not in HIDDEN_ROUTES and page.name not in route_names
    )

    # Russian labels take precedence over Page titles from the DB, which are English.
    return [
        {
            "label": DEFAULT_ROUTE_LABELS.get(route) or page_map.get(route, route),
            "route": route,
        }
        for route in route_names
    ]
