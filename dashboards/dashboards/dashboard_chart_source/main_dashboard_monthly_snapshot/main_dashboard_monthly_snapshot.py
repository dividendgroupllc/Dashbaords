from __future__ import annotations

import frappe
from dashboards.dashboards.dashboard_chart_source.main_dashboard_monthly_snapshot_source.main_dashboard_monthly_snapshot_source import (
    get_data as get_monthly_snapshot_source_data,
)


@frappe.whitelist()
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
    return get_monthly_snapshot_source_data(
        chart_name=chart_name,
        chart=chart,
        no_cache=no_cache,
        filters=filters,
        from_date=from_date,
        to_date=to_date,
        timespan=timespan,
        time_interval=time_interval,
        heatmap_year=heatmap_year,
    )
