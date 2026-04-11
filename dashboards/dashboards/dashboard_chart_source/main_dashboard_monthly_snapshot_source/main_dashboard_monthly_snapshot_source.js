frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Main Dashboard Monthly Snapshot Source"] = {
	method: "dashboards.dashboards.dashboard_chart_source.main_dashboard_monthly_snapshot_source.main_dashboard_monthly_snapshot_source.get_data",
	filters: [],
};
