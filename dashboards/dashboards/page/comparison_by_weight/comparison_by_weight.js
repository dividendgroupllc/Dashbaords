frappe.pages["comparison-by-weight"].on_page_load = function (wrapper) {
	new dashboards.ui.ComparisonByWeightPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.ComparisonByWeightPage = class ComparisonByWeightPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Comparison by Weight"),
			single_column: true,
		});

		this.state = {
			month: null,
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("comparison-by-weight-layout");
		this.wrapper.find(".page-head").addClass("comparison-by-weight-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="comparison-by-weight-screen">
				<div class="comparison-by-weight-shell">
					<section class="comparison-by-weight-months" data-region="months"></section>
					<section class="comparison-by-weight-grid">
						<div class="comparison-by-weight-panel">
							<div class="comparison-by-weight-table-wrap" data-region="customer-table"></div>
						</div>
						<div class="comparison-by-weight-panel">
							<div class="comparison-by-weight-table-wrap" data-region="item-table"></div>
						</div>
					</section>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "comparison-by-weight",
		});

		this.$months = this.page.main.find('[data-region="months"]');
		this.$customerTable = this.page.main.find('[data-region="customer-table"]');
		this.$itemTable = this.page.main.find('[data-region="item-table"]');
	}

	load_context(filters = {}) {
		frappe.call({
			method: "dashboards.dashboards.page.comparison_by_weight.comparison_by_weight.get_dashboard_context",
			args: {
				month: filters.month || this.state.month,
			},
			callback: (r) => {
				this.context = r.message || {};
				this.state.month = this.context.selected_month || null;
				this.render();
			},
		});
	}

	render() {
		this.renderMonths();
		this.renderCustomerTable();
		this.renderItemTable();
	}

	renderMonths() {
		const months = this.context.months || [];
		this.$months.html(
			months
				.map(
					(month) => `
						<button class="comparison-by-weight-month ${month.key === this.state.month ? "is-active" : ""}" data-month="${month.key}">
							${frappe.utils.escape_html(month.label)}
						</button>
					`
				)
				.join("")
		);

		this.$months.find("[data-month]").on("click", (event) => {
			this.load_context({
				month: String($(event.currentTarget).data("month")),
			});
		});
	}

	renderCustomerTable() {
		const years = this.context.years || [];
		const rows = this.context.customer_rows || [];

		this.$customerTable.html(`
			<table class="comparison-by-weight-table">
				<thead>
					<tr>
						<th class="comparison-by-weight-name comparison-by-weight-name--customer">${frappe.utils.escape_html(
							this.context.customer_title || "Клиент кг"
						)}</th>
						${years.map((year) => `<th>${frappe.utils.escape_html(String(year))}</th>`).join("")}
						<th>${frappe.utils.escape_html(this.context.total_title || "Total")}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr class="${row.is_total ? "is-total" : ""}">
									<td class="comparison-by-weight-name-cell comparison-by-weight-name--customer">${frappe.utils.escape_html(
										row.label || ""
									)}</td>
									${(row.values || []).map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || ""))}</td>`).join("")}
									<td class="is-number comparison-by-weight-total-cell">${frappe.utils.escape_html(String(row.total || ""))}</td>
								</tr>
							`
						)
						.join("")}
				</tbody>
			</table>
		`);
	}

	renderItemTable() {
		const years = this.context.years || [];
		const rows = this.context.item_rows || [];

		this.$itemTable.html(`
			<table class="comparison-by-weight-table comparison-by-weight-table--items">
				<thead>
					<tr>
						<th class="comparison-by-weight-name comparison-by-weight-name--item">Year</th>
						${years
							.map(
								(year) => `
									<th colspan="2">${frappe.utils.escape_html(String(year))}</th>
								`
							)
							.join("")}
						<th colspan="2">${frappe.utils.escape_html(this.context.total_title || "Total")}</th>
					</tr>
					<tr>
						<th class="comparison-by-weight-name comparison-by-weight-name--item">${frappe.utils.escape_html(
							this.context.item_title || "Предмет кг"
						)}</th>
						${years
							.map(
								() => `
									<th>${frappe.utils.escape_html(this.context.qty_title || "КГ")}</th>
									<th>${frappe.utils.escape_html(this.context.avg_title || "Сред цена")}</th>
								`
							)
							.join("")}
						<th>${frappe.utils.escape_html(this.context.total_qty_title || "KG")}</th>
						<th>${frappe.utils.escape_html(this.context.total_avg_title || "Сред цена")}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr class="${row.is_total ? "is-total" : ""}">
									<td class="comparison-by-weight-name-cell comparison-by-weight-name--item">${frappe.utils.escape_html(
										row.label || ""
									)}</td>
									${(row.values || []).map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || ""))}</td>`).join("")}
									<td class="is-number comparison-by-weight-total-cell">${frappe.utils.escape_html(String(row.total_qty || ""))}</td>
									<td class="is-number comparison-by-weight-total-cell">${frappe.utils.escape_html(String(row.total_avg || ""))}</td>
								</tr>
							`
						)
						.join("")}
				</tbody>
			</table>
		`);
	}
};
