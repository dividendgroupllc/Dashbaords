frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Main Dashboard Monthly Snapshot Source"] = {
	method: "dashboards.dashboards.dashboard_chart_source.main_dashboard_monthly_snapshot.main_dashboard_monthly_snapshot.get_data",
	filters: [],
};
