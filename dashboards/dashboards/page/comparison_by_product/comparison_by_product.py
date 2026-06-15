from __future__ import annotations

import frappe
from dashboards.dashboards.cache import dashboard_cache

from dashboards.dashboards.page.comparison_by_product.data import (
    get_dashboard_context as get_comparison_by_product_context,
)


@frappe.whitelist()
@dashboard_cache("comparison_by_product")
def get_dashboard_context():
    return get_comparison_by_product_context()
