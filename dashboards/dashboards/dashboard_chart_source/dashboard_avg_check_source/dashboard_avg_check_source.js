frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Dashboard Avg Check Source"] = {
	method: "dashboards.dashboards.dashboard_chart_source.dashboard_avg_check_source.dashboard_avg_check_source.get_data",
	filters: [],
};
