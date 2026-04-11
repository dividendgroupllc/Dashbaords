frappe.pages["page-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.PageDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.PageDashboardPage = class PageDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Dashboard"),
			single_column: true,
		});
		this.selectedYear = "2024";
		this.kpiCards = {
			sales_total: "Dashboard KPI Sales Total",
			cost_total: "Dashboard KPI Cost Total",
			margin_total: "Dashboard KPI Margin Total",
			rsp_total: "Dashboard KPI RSP Total",
			return_total: "Dashboard KPI Return Total",
			kg_total: "Dashboard KPI Kg Total",
			avg_check: "Dashboard KPI Avg Check",
		};
		this.charts = {
			price_trend: "Dashboard Avg Cost Chart",
			check_trend: "Dashboard Avg Check Chart",
			kg_trend: "Dashboard Product Kg Chart",
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("dashboard-page-layout");
		this.wrapper.find(".page-head").addClass("dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="dashboard-page-screen">
				<div class="dashboard-page-shell">
					<div class="dashboard-page-tabs" data-region="tabs"></div>
					<div class="dashboard-page-kpis" data-region="kpis"></div>
					<div class="dashboard-page-middle">
						<div class="dashboard-page-column dashboard-page-column--left">
							<div class="dashboard-page-card dashboard-page-card--paired">
								<div class="dashboard-page-paired-tables">
									<div class="dashboard-page-table-slot" data-table="sales-by-month"></div>
									<div class="dashboard-page-table-slot" data-table="returns-by-month"></div>
								</div>
							</div>
						</div>
						<div class="dashboard-page-column dashboard-page-column--center">
							<div class="dashboard-page-card">
								<div class="dashboard-page-year-filter" data-region="years"></div>
								<div class="dashboard-page-table-slot" data-table="product-margin"></div>
							</div>
						</div>
						<div class="dashboard-page-column dashboard-page-column--right">
							<div class="dashboard-page-card">
								<div class="dashboard-page-table-slot" data-table="client-kpi"></div>
							</div>
						</div>
					</div>
					<div class="dashboard-page-bottom">
						<div class="dashboard-page-card dashboard-page-chart-card">
							<div class="dashboard-page-chart-title">ойма-ой narx-нарх динамикаси</div>
							<div data-chart="price_trend"></div>
						</div>
						<div class="dashboard-page-card dashboard-page-chart-card">
							<div class="dashboard-page-chart-title">Ойма-ой нарх динамикаси</div>
							<div data-chart="check_trend"></div>
						</div>
						<div class="dashboard-page-card dashboard-page-chart-card">
							<div class="dashboard-page-chart-title">Ойма-ой сотилган товар килода</div>
							<div data-chart="kg_trend"></div>
						</div>
						<div class="dashboard-page-card">
							<div class="dashboard-page-table-slot" data-table="regional-summary"></div>
						</div>
					</div>
				</div>
			</div>
		`);

		this.$tabs = this.page.main.find('[data-region="tabs"]');
		this.$kpis = this.page.main.find('[data-region="kpis"]');
		this.$years = this.page.main.find('[data-region="years"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.page_dashboard.page_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.render();
			},
		});
	}

	render() {
		this.render_tabs();
		this.render_kpis();
		this.render_year_buttons();
		this.render_tables();
		this.render_charts();
	}

	render_tabs() {
		const tabs = this.context.tabs || [];
		this.$tabs.html(
			tabs
				.map(
					(tab) => `
						<button class="dashboard-page-tab ${tab.active ? "is-active" : ""}" data-route="${tab.route}">
							${frappe.utils.escape_html(tab.label)}
						</button>
					`
				)
				.join("")
		);

		this.$tabs.find(".dashboard-page-tab").on("click", (e) => {
			const route = $(e.currentTarget).data("route");
			if (route) {
				frappe.set_route(route.replace(/^\/app\//, ""));
			}
		});
	}

	render_kpis() {
		const kpis = this.context.kpis || [];
		this.$kpis.html(
			kpis
				.map(
					(kpi) => `
						<div class="dashboard-page-card dashboard-page-kpi-card">
							<div class="dashboard-page-kpi-number" data-kpi-card="${kpi.key}"></div>
							<div class="dashboard-page-kpi-label">${frappe.utils.escape_html(kpi.label)}</div>
							${kpi.subtext ? `<div class="dashboard-page-kpi-subtext">${frappe.utils.escape_html(kpi.subtext)}</div>` : ""}
						</div>
					`
				)
				.join("")
		);

		kpis.forEach((kpi) => {
			this.mount_number_card(this.page.main.find(`[data-kpi-card="${kpi.key}"]`), this.kpiCards[kpi.key]);
		});
	}

	render_year_buttons() {
		const years = this.context.years || [];
		this.$years.html(
			years
				.map(
					(year) => `
						<button class="dashboard-page-year ${year === this.selectedYear ? "is-active" : ""}" data-year="${year}">
							${frappe.utils.escape_html(year)}
						</button>
					`
				)
				.join("") + '<div class="dashboard-page-year-spinner">•<br>•</div>'
		);

		this.$years.find(".dashboard-page-year").on("click", (e) => {
			this.selectedYear = String($(e.currentTarget).data("year"));
			this.render_year_buttons();
			this.render_tables();
		});
	}

	render_tables() {
		this.render_table("sales-by-month", this.context.sales_by_month, ["Month", "Сумма.прод"]);
		this.render_table("returns-by-month", this.context.returns_by_month, ["Month", "Возврат"]);
		this.render_table(
			"product-margin",
			(this.context.product_margin_by_year || {})[this.selectedYear] || [],
			["Предметы", "Маржа", "Рен"]
		);
		this.render_table("client-kpi", this.context.client_kpi, ["Клиент", "КГ", "Сумма.прод", "Рен"]);
		this.render_table("regional-summary", this.context.regional_summary, ["Город", "Сумма", "Маржа", "Рен"]);
	}

	render_table(key, rows, headers) {
		const $slot = this.page.main.find(`[data-table="${key}"]`);
		$slot.html(`
			<table class="dashboard-page-table">
				<thead>
					<tr>${headers.map((header) => `<th>${frappe.utils.escape_html(header)}</th>`).join("")}</tr>
				</thead>
				<tbody>
					${(rows || [])
						.map(
							(row) => `
								<tr class="${row.is_total ? "is-total" : ""}">
									${row.values
										.map((value, index) => {
											const alignClass = index === 0 ? "is-text" : "is-number";
											return `<td class="${alignClass}">${frappe.utils.escape_html(String(value))}</td>`;
										})
										.join("")}
								</tr>
							`
						)
						.join("")}
				</tbody>
			</table>
		`);
	}

	render_charts() {
		Object.entries(this.charts).forEach(([key, chartName]) => {
			const $container = this.page.main.find(`[data-chart="${key}"]`);
			this.mount_chart($container, chartName, 178);
		});
	}

	mount_chart($container, chartName, height) {
		$container.empty();
		frappe.widget.make_widget({
			widget_type: "chart",
			container: $container,
			label: chartName,
			chart_name: chartName,
			name: chartName,
			height: height,
			width: "Full",
		});
	}

	mount_number_card($container, cardName) {
		$container.empty();
		frappe.widget.make_widget({
			widget_type: "number_card",
			container: $container,
			label: cardName,
			number_card_name: cardName,
			name: cardName,
		});
	}
};
