from __future__ import annotations

import frappe
from frappe.utils.dashboard import cache_source

from dashboards.dashboards.dashboard_data import MONTH_LABELS, get_monthly_sales_kg


@frappe.whitelist()
@cache_source
def get_data(
    chart_name=None,
    chart=None,
    no_cache=None,
    filters=None,
    from_date=None,
    to_date=None,
    timespan=None,
    time_interval=None,
    heatmap_year=None,
):
    labels = []
    values = []

    for row in get_monthly_sales_kg(year_limit=4):
        for month_name, month_value in zip(MONTH_LABELS, row["values"]):
            labels.append(f"{month_name}\n{row['year']}")
            values.append(month_value)

    return {
        "labels": labels,
        "datasets": [
            {
                "name": "KG",
                "values": values,
            }
        ],
    }
