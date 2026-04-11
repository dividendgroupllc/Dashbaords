frappe.pages["sales-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.SalesDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.SalesDashboardPage = class SalesDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Sales Dashboard"),
			single_column: true,
		});

		this.state = {
			year: null,
			month: null,
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("sales-dashboard-layout");
		this.wrapper.find(".page-head").addClass("sales-dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="sales-dashboard-screen">
				<div class="sales-dashboard-shell">
					<div class="sales-dashboard-filters sales-dashboard-filters--years" data-region="years"></div>
					<div class="sales-dashboard-filters sales-dashboard-filters--months" data-region="months"></div>
					<div class="sales-dashboard-table-panel">
						<div class="sales-dashboard-table-wrap" data-region="table"></div>
					</div>
				</div>
			</div>
		`);

		this.$years = this.page.main.find('[data-region="years"]');
		this.$months = this.page.main.find('[data-region="months"]');
		this.$table = this.page.main.find('[data-region="table"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.sales_dashboard.sales_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.state = { ...(this.context.default_filters || {}) };
				this.render();
			},
		});
	}

	render() {
		this.render_years();
		this.render_months();
		this.render_table();
	}

	render_years() {
		const years = this.context.years || [];
		this.$years.html(
			years
				.map(
					(year) => `
						<button class="sales-dashboard-chip sales-dashboard-chip--year ${year === this.state.year ? "is-active" : ""}" data-year="${year}">
							${frappe.utils.escape_html(year)}
						</button>
					`
				)
				.join("") +
				`<div class="sales-dashboard-year-spinner"><span></span><span></span></div>`
		);

		this.$years.find("[data-year]").on("click", (e) => {
			this.state.year = String($(e.currentTarget).data("year"));
			this.render_table();
			this.render_years();
		});
	}

	render_months() {
		const months = this.context.months || [];
		this.$months.html(
			months
				.map(
					(month) => `
						<button class="sales-dashboard-chip sales-dashboard-chip--month ${month.key === this.state.month ? "is-active" : ""}" data-month="${month.key}">
							${frappe.utils.escape_html(month.label)}
						</button>
					`
				)
				.join("")
		);

		this.$months.find("[data-month]").on("click", (e) => {
			this.state.month = String($(e.currentTarget).data("month"));
			this.render_table();
			this.render_months();
		});
	}

	render_table() {
		const rows = this.getRowsForFilters();
		const total = this.buildTotalRow(rows);
		const headers = ["Предметы", "КГ", "Сумма.прод", "Сумма себест", "Маржа", "РСП сумма", "рен", "Прибыль"];

		this.$table.html(`
			<table class="sales-dashboard-table">
				<thead>
					<tr>${headers.map((header, index) => `<th class="${index === 0 ? "is-text" : "is-number"}">${header}</th>`).join("")}</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr>
									<td class="is-text">${frappe.utils.escape_html(row.item)}</td>
									<td class="is-number">${this.formatInteger(row.kg)}</td>
									<td class="is-number">${this.formatInteger(row.sales)}</td>
									<td class="is-number">${this.formatInteger(row.cost)}</td>
									<td class="is-number">${this.formatInteger(row.margin)}</td>
									<td class="is-number">${this.formatInteger(row.rsp)}</td>
									<td class="is-number">${this.formatPercent(row.margin_percent)}</td>
									<td class="is-number ${row.profit < 0 ? "is-negative" : ""}">${this.formatInteger(row.profit)}</td>
								</tr>
							`
						)
						.join("")}
					<tr class="is-total">
						<td class="is-text">Total</td>
						<td class="is-number">${this.formatInteger(total.kg)}</td>
						<td class="is-number">${this.formatInteger(total.sales)}</td>
						<td class="is-number">${this.formatInteger(total.cost)}</td>
						<td class="is-number">${this.formatInteger(total.margin)}</td>
						<td class="is-number">${this.formatInteger(total.rsp)}</td>
						<td class="is-number">${this.formatPercent(total.margin_percent)}</td>
						<td class="is-number ${total.profit < 0 ? "is-negative" : ""}">${this.formatInteger(total.profit)}</td>
					</tr>
				</tbody>
			</table>
		`);
	}

	getRowsForFilters() {
		const baseRows = this.context.product_rows || [];
		const yearFactorMap = {
			"2021": 0.82,
			"2023": 0.93,
			"2024": 1,
			"2025": 1.06,
		};
		const monthIndex = (this.context.months || []).findIndex((month) => month.key === this.state.month);
		const monthFactor = 0.7 + (Math.max(monthIndex, 0) * 0.028);
		const factor = (yearFactorMap[this.state.year] || 1) * monthFactor;

		return baseRows.map((row, rowIndex) => {
			const variance = 1 + ((rowIndex % 5) * 0.012);
			const kg = Math.round(row.kg * factor * variance);
			const sales = Math.round(row.sales * factor * variance);
			const cost = Math.round(row.cost * factor * (0.988 + ((rowIndex + monthIndex) % 4) * 0.011));
			const margin = sales - cost;
			const rsp = Math.round(margin * (0.34 + ((rowIndex + 1) % 3) * 0.03));
			const profit = margin - rsp;
			return {
				item: row.item,
				kg: kg,
				sales: sales,
				cost: cost,
				margin: margin,
				rsp: rsp,
				margin_percent: sales ? (margin / sales) * 100 : 0,
				profit: profit,
			};
		});
	}

	buildTotalRow(rows) {
		const total = rows.reduce(
			(accumulator, row) => {
				accumulator.kg += row.kg;
				accumulator.sales += row.sales;
				accumulator.cost += row.cost;
				accumulator.margin += row.margin;
				accumulator.rsp += row.rsp;
				accumulator.profit += row.profit;
				return accumulator;
			},
			{ kg: 0, sales: 0, cost: 0, margin: 0, rsp: 0, profit: 0 }
		);

		total.margin_percent = total.sales ? (total.margin / total.sales) * 100 : 0;
		return total;
	}

	formatInteger(value) {
		const sign = value < 0 ? "-" : "";
		const numeric = Math.abs(Math.round(value));
		return `${sign}${String(numeric).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}`;
	}

	formatPercent(value) {
		return `${Number(value || 0).toFixed(1).replace(".", ",")}%`;
	}
};
