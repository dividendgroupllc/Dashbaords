frappe.pages["comparison-by-amount"].on_page_load = function (wrapper) {
	new dashboards.ui.ComparisonByAmountPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.ComparisonByAmountPage = class ComparisonByAmountPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Comparison by Amount"),
			single_column: true,
		});

		this.state = {
			month: null,
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("comparison-by-amount-layout");
		this.wrapper.find(".page-head").addClass("comparison-by-amount-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="comparison-by-amount-screen">
				<div class="comparison-by-amount-shell">
					<section class="comparison-by-amount-months" data-region="months"></section>
					<section class="comparison-by-amount-grid">
						<div class="comparison-by-amount-panel">
							<div class="comparison-by-amount-table-wrap" data-region="customer-table"></div>
						</div>
						<div class="comparison-by-amount-panel">
							<div class="comparison-by-amount-table-wrap" data-region="item-table"></div>
						</div>
					</section>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "comparison-by-amount",
		});

		this.$months = this.page.main.find('[data-region="months"]');
		this.$customerTable = this.page.main.find('[data-region="customer-table"]');
		this.$itemTable = this.page.main.find('[data-region="item-table"]');
	}

	load_context(filters = {}) {
		frappe.call({
			method: "dashboards.dashboards.page.comparison_by_amount.comparison_by_amount.get_dashboard_context",
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
						<button class="comparison-by-amount-month ${month.key === this.state.month ? "is-active" : ""}" data-month="${month.key}">
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
			<table class="comparison-by-amount-table">
				<thead>
					<tr>
						<th class="comparison-by-amount-name comparison-by-amount-name--customer">${frappe.utils.escape_html(
							this.context.customer_title || "Клиент сумма"
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
									<td class="comparison-by-amount-name-cell comparison-by-amount-name--customer">${frappe.utils.escape_html(
										row.label || ""
									)}</td>
									${(row.values || []).map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || ""))}</td>`).join("")}
									<td class="is-number comparison-by-amount-total-cell">${frappe.utils.escape_html(String(row.total || ""))}</td>
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
			<table class="comparison-by-amount-table comparison-by-amount-table--items">
				<thead>
					<tr>
						<th class="comparison-by-amount-name comparison-by-amount-name--item">Year</th>
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
						<th class="comparison-by-amount-name comparison-by-amount-name--item">${frappe.utils.escape_html(
							this.context.item_title || "Предметы сумма"
						)}</th>
						${years
							.map(
								() => `
									<th>${frappe.utils.escape_html(this.context.amount_title || "Сумма")}</th>
									<th>${frappe.utils.escape_html(this.context.avg_title || "Сре.чек")}</th>
								`
							)
							.join("")}
						<th>${frappe.utils.escape_html(this.context.total_amount_title || "Сумма")}</th>
						<th>${frappe.utils.escape_html(this.context.total_avg_title || "Сре.чек")}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr class="${row.is_total ? "is-total" : ""}">
									<td class="comparison-by-amount-name-cell comparison-by-amount-name--item">${frappe.utils.escape_html(
										row.label || ""
									)}</td>
									${(row.values || []).map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || ""))}</td>`).join("")}
									<td class="is-number comparison-by-amount-total-cell">${frappe.utils.escape_html(String(row.total_amount || ""))}</td>
									<td class="is-number comparison-by-amount-total-cell">${frappe.utils.escape_html(String(row.total_avg || ""))}</td>
								</tr>
							`
						)
						.join("")}
				</tbody>
			</table>
		`);
	}
};
