frappe.pages["kpi-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.KPIDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.KPIDashboardPage = class KPIDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("KPI"),
			single_column: true,
		});
		this.selectedYear = "2024";
		this.selectedMonth = "January";
		this.kpiCards = {
			sales: "KPI Dashboard Sales Total",
			margin: "KPI Dashboard Margin Total",
			margin_minus_discount: "KPI Dashboard Margin Minus Discount",
			returns: "KPI Dashboard Returns Total",
			bonus: "KPI Dashboard Bonus Total",
			discount: "KPI Dashboard Discount Total",
		};

		this.make_layout();
		this.load_data();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("kpi-dashboard-layout");
		this.wrapper.find(".page-head").addClass("kpi-dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="kpi-dashboard-screen">
				<div class="kpi-dashboard-header">
					<div class="kpi-dashboard-title">KPI</div>
				</div>
				<div class="kpi-dashboard-body">
					<aside class="kpi-dashboard-sidebar">
						<div class="kpi-dashboard-filter-card">
							<div class="kpi-dashboard-filter-title">Year</div>
							<div class="kpi-dashboard-year-list" data-region="years"></div>
						</div>
						<div class="kpi-dashboard-filter-card">
							<div class="kpi-dashboard-filter-title">Month</div>
							<div class="kpi-dashboard-month-list" data-region="months"></div>
						</div>
					</aside>
					<section class="kpi-dashboard-main">
						<div class="kpi-dashboard-kpis" data-region="kpis"></div>
						<div class="kpi-dashboard-card">
							<div class="kpi-dashboard-table-wrap" data-region="client-table"></div>
						</div>
						<div class="kpi-dashboard-bottom">
							<div class="kpi-dashboard-card">
								<div class="kpi-dashboard-subtitle">Client Summary</div>
								<div class="kpi-dashboard-table-wrap" data-region="aggregate-table"></div>
							</div>
							<div class="kpi-dashboard-card">
								<div class="kpi-dashboard-subtitle">Client Distribution</div>
								<div class="kpi-dashboard-treemap" data-region="treemap"></div>
							</div>
						</div>
					</section>
				</div>
			</div>
		`);

		this.$years = this.page.main.find('[data-region="years"]');
		this.$months = this.page.main.find('[data-region="months"]');
		this.$kpis = this.page.main.find('[data-region="kpis"]');
		this.$clientTable = this.page.main.find('[data-region="client-table"]');
		this.$aggregateTable = this.page.main.find('[data-region="aggregate-table"]');
		this.$treemap = this.page.main.find('[data-region="treemap"]');
	}

	load_data() {
		frappe.call({
			method: "dashboards.dashboards.page.kpi_dashboard.kpi_dashboard.get_kpi_dashboard_data",
			args: {
				year: this.selectedYear,
				month: this.selectedMonth,
			},
			callback: (r) => {
				this.data = r.message || {};
				this.selectedYear = this.data.selected_year || this.selectedYear;
				this.selectedMonth = this.data.selected_month || this.selectedMonth;
				this.render();
			},
		});
	}

	render() {
		this.render_years();
		this.render_months();
		this.render_kpis();
		this.render_client_table();
		this.render_aggregate_table();
		this.render_treemap();
	}

	render_years() {
		this.$years.html(
			(this.data.years || [])
				.map(
					(year) => `
						<button class="kpi-dashboard-year ${year === this.selectedYear ? "is-active" : ""}" data-year="${year}">
							${frappe.utils.escape_html(year)}
						</button>
					`
				)
				.join("")
		);

		this.$years.find(".kpi-dashboard-year").on("click", (e) => {
			this.selectedYear = $(e.currentTarget).data("year");
			this.load_data();
		});
	}

	render_months() {
		this.$months.html(
			(this.data.months || [])
				.map(
					(month) => `
						<button class="kpi-dashboard-month ${month === this.selectedMonth ? "is-active" : ""}" data-month="${month}">
							${frappe.utils.escape_html(month)}
						</button>
					`
				)
				.join("")
		);

		this.$months.find(".kpi-dashboard-month").on("click", (e) => {
			this.selectedMonth = $(e.currentTarget).data("month");
			this.load_data();
		});
	}

	render_kpis() {
		const labels = [
			["sales", "Sales"],
			["margin", "Margin"],
			["margin_minus_discount", "Margin Minus Discount"],
			["returns", "Returns"],
			["bonus", "Bonus"],
			["discount", "Discount"],
		];

		this.$kpis.html(
			labels
				.map(
					([key, label]) => `
						<div class="kpi-dashboard-card kpi-dashboard-kpi-card">
							<div class="kpi-dashboard-kpi-value" data-kpi-card="${key}"></div>
							<div class="kpi-dashboard-kpi-label">${frappe.utils.escape_html(label)}</div>
						</div>
					`
				)
				.join("")
		);

		labels.forEach(([key]) => {
			this.mount_number_card(this.$kpis.find(`[data-kpi-card="${key}"]`), this.kpiCards[key]);
		});
	}

	render_client_table() {
		const headers = ["Client", "Sales", "Cost", "Qty", "Returns", "Margin", "%", "Bonus", "Discount", "Profitability"];
		this.$clientTable.html(this.make_table(headers, this.data.client_rows || [], "wide"));
	}

	render_aggregate_table() {
		const headers = ["Group", "Sales", "Margin", "%"];
		this.$aggregateTable.html(this.make_table(headers, this.data.aggregate_rows || [], "compact"));
	}

	make_table(headers, rows, variant) {
		return `
			<table class="kpi-dashboard-table kpi-dashboard-table--${variant}">
				<thead>
					<tr>${headers.map((header) => `<th>${frappe.utils.escape_html(header)}</th>`).join("")}</tr>
				</thead>
				<tbody>
					${rows
						.map((row) => {
							const isTotal = row[row.length - 1] === true;
							const values = isTotal ? row.slice(0, -1) : row;
							return `
								<tr class="${isTotal ? "is-total" : ""}">
									${values
										.map((value, index) => {
											const alignClass = index === 0 ? "is-text" : "is-number";
											return `<td class="${alignClass}">${frappe.utils.escape_html(String(value))}</td>`;
										})
										.join("")}
								</tr>
							`;
						})
						.join("")}
				</tbody>
			</table>
		`;
	}

	render_treemap() {
		const items = this.data.treemap || [];
		const total = items.reduce((sum, item) => sum + item.value, 0) || 1;
		const palette = ["#128c3a", "#18a646", "#22ba52", "#39c965", "#62d880", "#8fe6a6", "#baf2c6", "#dff9e6"];

		this.$treemap.html(
			items
				.map((item, index) => {
					const width = Math.max(18, Math.round((item.value / total) * 100));
					return `
						<div class="kpi-dashboard-treemap-item" style="flex:${width}; background:${palette[index % palette.length]}">
							<div class="kpi-dashboard-treemap-name">${frappe.utils.escape_html(item.label)}</div>
							<div class="kpi-dashboard-treemap-value">${frappe.utils.escape_html(frappe.format(item.value, { fieldtype: "Int" }))}</div>
						</div>
					`;
				})
				.join("")
		);
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
