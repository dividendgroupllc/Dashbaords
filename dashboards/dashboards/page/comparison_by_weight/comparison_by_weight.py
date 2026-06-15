from __future__ import annotations

import frappe
from dashboards.dashboards.cache import dashboard_cache

from dashboards.dashboards.page.comparison_by_weight.data import (
	get_dashboard_context as get_comparison_by_weight_context,
)


@frappe.whitelist()
@dashboard_cache("comparison_by_weight")
def get_dashboard_context(month: str | None = None):
	return get_comparison_by_weight_context(month=month)
