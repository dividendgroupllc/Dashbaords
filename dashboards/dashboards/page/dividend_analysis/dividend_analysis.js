frappe.pages["dividend-analysis"].on_page_load = function (wrapper) {
	new dashboards.ui.DividendAnalysisPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.DividendAnalysisPage = class DividendAnalysisPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Dividend Analysis"),
			single_column: true,
		});

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("dividend-analysis-layout");
		this.wrapper.find(".page-head").addClass("dividend-analysis-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="dividend-analysis-screen">
				<div class="dividend-analysis-shell">
					<header class="dividend-analysis-hero">
						<div class="dividend-analysis-brand">
							<div class="dividend-analysis-brand-mark">PM</div>
							<div class="dividend-analysis-brand-copy">
								<div class="dividend-analysis-title">3 ИНФОРМАЦИОННАЯ ПАНЕЛЬ</div>
								<div class="dividend-analysis-subtitle">КОМПАНИЯ</div>
							</div>
						</div>
						<div class="dividend-analysis-info-icon" aria-hidden="true">i</div>
					</header>
					<div class="dividend-analysis-toolbar">
						<div class="dividend-analysis-toolbar-title">Топилган даромад йиллар кесимида ойма-ой куринишда</div>
						<div class="dividend-analysis-toolbar-title dividend-analysis-toolbar-title--right">
							Инвесторлар ким қайси ойи қанча пул олгани ва умумийси
						</div>
					</div>
					<div class="dividend-analysis-toolbar-meta" data-region="generated-at"></div>
					<div class="dividend-analysis-grid">
						<section class="dividend-analysis-column">
							<div class="dividend-analysis-card" data-card="outstanding"></div>
							<div class="dividend-analysis-card" data-card="investor-totals"></div>
						</section>
						<section class="dividend-analysis-column dividend-analysis-column--center">
							<div class="dividend-analysis-card dividend-analysis-card--stretch" data-card="monthly-breakdown"></div>
						</section>
						<section class="dividend-analysis-column">
							<div class="dividend-analysis-card" data-card="average"></div>
							<div class="dividend-analysis-card" data-card="invoice-count"></div>
						</section>
					</div>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "dividend-analysis",
		});

		this.$generatedAt = this.page.main.find('[data-region="generated-at"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.dividend_analysis.dividend_analysis.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.selectedYear = String(this.context.selected_year || "");
				this.render();
			},
		});
	}

	render() {
		this.$generatedAt.text(
			this.context.generated_at ? `${__("Последнее обновление")}: ${this.context.generated_at}` : ""
		);
		this.render_year_matrix_card({
			card: "outstanding",
			title: "Month",
			subtitle: "Инвесторлар учун умумий дебиторлик қолдиғи",
			columns: this.context.years || [],
			rows: this.build_simple_rows(this.context.outstanding_by_year || {}),
		});
		this.render_investor_totals_card();
		this.render_breakdown_card();
		this.render_year_matrix_card({
			card: "average",
			title: "Month",
			subtitle: "Инвесторлар ким қайси ой қанча пул олгани ва умумийси",
			columns: this.context.years || [],
			rows: this.build_simple_rows(this.context.average_by_year || {}),
		});
		this.render_year_matrix_card({
			card: "invoice-count",
			title: "Month",
			subtitle: "Ойлар кесимида ҳужжатлар сони",
			columns: this.context.years || [],
			rows: this.build_simple_rows(this.context.invoice_count_by_year || {}),
		});
	}

	render_investor_totals_card() {
		const years = this.context.years || [];
		const rows = this.build_simple_rows(this.context.investor_monthly_totals_by_year || {});
		const $card = this.page.main.find('[data-card="investor-totals"]');

		$card.html(`
			<div class="dividend-analysis-investor-total-title">
				Инвесторла умумий олган суммаси йиллар ва ойма ой куринишда
			</div>
			<div class="dividend-analysis-table-wrap dividend-analysis-table-wrap--investor-totals">
				<table class="dividend-analysis-table dividend-analysis-table--investor-totals">
					<thead>
						<tr>
							<th>Month</th>
							${years.map((year) => `<th>${frappe.utils.escape_html(String(year))}</th>`).join("")}
						</tr>
					</thead>
					<tbody>
						${rows
							.map(
								(row) => `
									<tr class="${row.is_total ? "is-total" : ""}">
										<td>${frappe.utils.escape_html(row.label || "")}</td>
										${(row.values || [])
											.map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || "0"))}</td>`)
											.join("")}
									</tr>
								`
							)
							.join("")}
					</tbody>
				</table>
			</div>
		`);
	}

	render_breakdown_card() {
		const $card = this.page.main.find('[data-card="monthly-breakdown"]');
		const investors = this.context.investors || [];
		const rows = (this.context.investor_monthly_breakdown || {})[this.selectedYear] || [];
		const headerCells = investors
			.map(
				(investor) =>
					`<th>${frappe.utils.escape_html(investor.label)}</th>`
			)
			.join("");

		$card.html(`
			<div class="dividend-analysis-card-head">
				<div class="dividend-analysis-card-head-main">
					<div class="dividend-analysis-card-title">Year</div>
					<div class="dividend-analysis-card-subtitle">${frappe.utils.escape_html(this.selectedYear || "")}</div>
				</div>
				<div class="dividend-analysis-year-picker">
					${(this.context.years || [])
						.map(
							(year) => `
								<button class="dividend-analysis-year-pill ${String(year) === this.selectedYear ? "is-active" : ""}" data-year="${year}">
									${frappe.utils.escape_html(String(year))}
								</button>
							`
						)
						.join("")}
				</div>
			</div>
			<div class="dividend-analysis-table-wrap">
				<table class="dividend-analysis-table dividend-analysis-table--dense">
					<thead>
						<tr>
							<th>Month</th>
							${headerCells}
							<th>Total</th>
						</tr>
					</thead>
					<tbody>
						${rows
							.map((row) => {
								const cells = investors
									.map(
										(investor) =>
											`<td class="is-number">${frappe.utils.escape_html(row.values?.[investor.key] || "0")}</td>`
									)
									.join("");
								return `
									<tr class="${row.is_total ? "is-total" : ""}">
										<td>${frappe.utils.escape_html(row.month || "")}</td>
										${cells}
										<td class="is-number">${frappe.utils.escape_html(row.total || "0")}</td>
									</tr>
								`;
							})
							.join("")}
					</tbody>
				</table>
			</div>
		`);

		$card.find(".dividend-analysis-year-pill").on("click", (event) => {
			this.selectedYear = String($(event.currentTarget).data("year"));
			this.render_breakdown_card();
		});
	}

	render_year_matrix_card({ card, title, subtitle, columns, rows, metaColumnLabel = "" }) {
		const $card = this.page.main.find(`[data-card="${card}"]`);
		$card.html(`
			<div class="dividend-analysis-card-head">
				<div class="dividend-analysis-card-title">${frappe.utils.escape_html(title)}</div>
				<div class="dividend-analysis-card-subtitle">${frappe.utils.escape_html(subtitle)}</div>
			</div>
			<div class="dividend-analysis-table-wrap">
				<table class="dividend-analysis-table">
					<thead>
						<tr>
							<th>${frappe.utils.escape_html(metaColumnLabel || "Month")}</th>
							${(columns || [])
								.map((column) => `<th>${frappe.utils.escape_html(String(column))}</th>`)
								.join("")}
						</tr>
					</thead>
					<tbody>
						${(rows || [])
							.map(
								(row) => `
									<tr class="${row.is_total ? "is-total" : ""}">
										<td>
											<div>${frappe.utils.escape_html(row.label || "")}</div>
											${row.meta ? `<div class="dividend-analysis-table-meta">${frappe.utils.escape_html(row.meta)}</div>` : ""}
										</td>
										${(row.values || [])
											.map((value) => `<td class="is-number">${frappe.utils.escape_html(String(value || "0"))}</td>`)
											.join("")}
									</tr>
								`
							)
							.join("")}
					</tbody>
				</table>
			</div>
		`);
	}

	build_simple_rows(dataset) {
		const months = this.context.months || [];
		const years = this.context.years || [];
		const rows = months.map((month, index) => ({
			label: month,
			values: years.map((year) => dataset?.[year]?.[index] || "0"),
		}));

		rows.push({
			label: "Total",
			values: years.map((year) => {
				const values = dataset?.[year] || [];
				return this.sumFormattedValues(values);
			}),
			is_total: true,
		});

		return rows;
	}

	sumFormattedValues(values) {
		const total = (values || []).reduce((accumulator, value) => {
			const normalized = Number(String(value || "0").replace(/\s/g, "").replace(",", "."));
			return accumulator + (Number.isFinite(normalized) ? normalized : 0);
		}, 0);

		return this.formatNumber(total);
	}

	formatNumber(value) {
		const number = Number(value || 0);
		return number.toLocaleString("en-US", {
			maximumFractionDigits: 2,
		}).replace(/,/g, " ");
	}
};
