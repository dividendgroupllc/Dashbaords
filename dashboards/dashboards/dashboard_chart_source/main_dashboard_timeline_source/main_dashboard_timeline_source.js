frappe.provide("frappe.dashboards.chart_sources");

frappe.dashboards.chart_sources["Main Dashboard Timeline Source"] = {
	method: "dashboards.dashboards.dashboard_chart_source.main_dashboard_timeline_source.main_dashboard_timeline_source.get_data",
	filters: [],
};
