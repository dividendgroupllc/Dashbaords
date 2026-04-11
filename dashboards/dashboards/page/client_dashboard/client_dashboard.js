frappe.pages["client-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.ClientDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.ClientDashboardPage = class ClientDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Client Dashboard"),
			single_column: true,
		});

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("main-dashboard-layout");
		this.page.main.removeClass("frappe-card");
		this.wrapper.find(".page-head").addClass("main-dashboard-page-head");

		this.page.main.html(`
			<div class="main-dashboard-screen">
				<div class="main-dashboard-panel">
					<div class="main-dashboard-tabs" data-region="tabs"></div>
					<div class="client-dashboard-content">
						<div class="client-dashboard-table-container" data-region="client-table"></div>
					</div>
				</div>
			</div>
		`);

		this.$tabs = this.page.main.find('[data-region="tabs"]');
		this.$clientTable = this.page.main.find('[data-region="client-table"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.client_dashboard.client_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.render_tabs();
				this.render_table();
			},
		});
	}

	render_tabs() {
		const tabs = this.context.tabs || [];
		this.$tabs.html(
			tabs
				.map(
					(tab) => `
						<button class="main-dashboard-tab ${tab.active ? "is-active" : ""}" data-route="${tab.route}">
							${frappe.utils.escape_html(tab.label)}
						</button>
					`
				)
				.join("")
		);

		this.$tabs.find(".main-dashboard-tab").on("click", (e) => {
			const route = $(e.currentTarget).data("route");
			if (route) {
				frappe.set_route(route.replace(/^\/app\//, ""));
			}
		});
	}

	render_table() {
		const clientData = this.context.client_data || [];
		const totalBalance = this.context.total_balance || 0;

		let tableHtml = `
			<table class="client-dashboard-table">
				<thead>
					<tr>
						<th class="text-left">${__("Клиент")}</th>
						<th class="text-right">${__("Сальдо на конец")}</th>
					</tr>
				</thead>
				<tbody>
					${clientData
						.map(
							(row) => `
						<tr>
							<td class="text-left">${frappe.utils.escape_html(row.client)}</td>
							<td class="text-right">${this.format_number(row.balance)}</td>
						</tr>
					`
						)
						.join("")}
				</tbody>
				<tfoot>
					<tr class="total-row">
						<td class="text-left font-bold">${__("Total")}</td>
						<td class="text-right font-bold">${this.format_number(totalBalance)}</td>
					</tr>
				</tfoot>
			</table>
		`;

		this.$clientTable.html(tableHtml);
	}

	format_number(val) {
		if (val === undefined || val === null) return "0";
		return val.toLocaleString("en-US").replace(/,/g, " ");
	}
};
