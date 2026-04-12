frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Dashboard Avg Cost Source"] = {
	method: "dashboards.dashboards.dashboard_chart_source.dashboard_avg_cost_source.dashboard_avg_cost_source.get_data",
	filters: [],
};
