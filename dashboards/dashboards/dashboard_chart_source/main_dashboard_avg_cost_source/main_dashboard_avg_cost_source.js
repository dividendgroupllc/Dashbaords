frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Main Dashboard Avg Cost Source"] = {
	method: "dashboards.dashboards.dashboard_chart_source.main_dashboard_avg_cost_source.main_dashboard_avg_cost_source.get_data",
	filters: [],
};
