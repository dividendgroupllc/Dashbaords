from __future__ import annotations

import frappe
from dashboards.dashboards.cache import dashboard_cache

from dashboards.dashboards.page.comparison_by_amount.data import get_dashboard_context as get_comparison_by_amount_context


@frappe.whitelist()
@dashboard_cache("comparison_by_amount")
def get_dashboard_context(month: str | None = None):
    return get_comparison_by_amount_context(month=month)

