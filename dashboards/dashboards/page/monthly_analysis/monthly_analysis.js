frappe.pages["monthly-analysis"].on_page_load = function (wrapper) {
	new dashboards.ui.MonthlyAnalysisPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.MonthlyAnalysisPage = class MonthlyAnalysisPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Monthly Analysis"),
			single_column: true,
		});

		this.state = {
			year: null,
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("monthly-analysis-layout");
		this.wrapper.find(".page-head").addClass("monthly-analysis-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="monthly-analysis-screen">
				<div class="monthly-analysis-shell">
					<section class="monthly-analysis-panel monthly-analysis-panel--top">
						<div class="monthly-analysis-table-wrap" data-region="clients-table"></div>
					</section>
					<section class="monthly-analysis-year-strip" data-region="years"></section>
					<section class="monthly-analysis-panel monthly-analysis-panel--bottom">
						<div class="monthly-analysis-table-wrap" data-region="items-table"></div>
					</section>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "monthly-analysis",
		});

		this.$years = this.page.main.find('[data-region="years"]');
		this.$clientsTable = this.page.main.find('[data-region="clients-table"]');
		this.$itemsTable = this.page.main.find('[data-region="items-table"]');
	}

	load_context(filters = {}) {
		frappe.call({
			method: "dashboards.dashboards.page.monthly_analysis.monthly_analysis.get_dashboard_context",
			args: {
				year: filters.year || this.state.year,
			},
			callback: (r) => {
				this.context = r.message || {};
				this.state.year = this.context.selected_year || null;
				this.render();
			},
		});
	}

	render() {
		this.render_years();
		this.renderTable({
			$target: this.$clientsTable,
			title: this.context.client_section_title || "Клиент кг",
			rows: this.context.client_rows || [],
			nameClass: "monthly-analysis-table-name--client",
		});
		this.renderTable({
			$target: this.$itemsTable,
			title: this.context.item_section_title || "Предметы кг",
			rows: this.context.item_rows || [],
			nameClass: "monthly-analysis-table-name--item",
		});
	}

	render_years() {
		const years = this.context.years || [];
		const hasOverflow = years.length > 6;
		const stripClass = hasOverflow ? "is-scrollable" : "is-centered";
		this.$years.html(
			`
				<div class="monthly-analysis-year-group-wrap ${stripClass}">
					<div class="monthly-analysis-year-group">
					${years
						.map(
							(year) => `
								<button class="monthly-analysis-year-pill ${String(year) === String(this.state.year) ? "is-active" : ""}" data-year="${year}">
									${frappe.utils.escape_html(String(year))}
								</button>
							`
						)
						.join("")}
					</div>
				</div>
			`
		);

		this.$years.find("[data-year]").on("click", (event) => {
			this.load_context({
				year: String($(event.currentTarget).data("year")),
			});
		});
	}

	renderTable({ $target, title, rows, nameClass }) {
		const months = this.context.months || [];
		$target.html(`
			<table class="monthly-analysis-table">
				<thead>
					<tr>
						<th class="monthly-analysis-table-name ${nameClass}">${frappe.utils.escape_html(title)}</th>
						${months.map((month) => `<th>${frappe.utils.escape_html(month)}</th>`).join("")}
						<th>Total</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr class="${row.is_total ? "is-total" : ""}">
									<td class="monthly-analysis-table-name-cell ${nameClass}">${frappe.utils.escape_html(row.label || "")}</td>
									${(row.values || [])
										.map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || ""))}</td>`)
										.join("")}
									<td class="is-number is-total-value">${frappe.utils.escape_html(String(row.total || ""))}</td>
								</tr>
							`
						)
						.join("")}
				</tbody>
			</table>
		`);
	}
};
