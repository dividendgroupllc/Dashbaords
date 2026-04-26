frappe.pages["page-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.PageDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.PageDashboardPage = class PageDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Панель"),
			single_column: true,
		});
		this.selectedYear = null;
		this.charts = {
			price_trend: { valueLabel: "Средняя себестоимость", totalLabel: "Макс" },
			check_trend: { valueLabel: "Средний чек", totalLabel: "Макс" },
			kg_trend: { valueLabel: "КГ", totalLabel: "Всего" },
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
							<div class="dashboard-page-chart-title">Динамика себестоимости по месяцам</div>
							<div data-chart="price_trend"></div>
						</div>
						<div class="dashboard-page-card dashboard-page-chart-card">
							<div class="dashboard-page-chart-title">Динамика среднего чека по месяцам</div>
							<div data-chart="check_trend"></div>
						</div>
						<div class="dashboard-page-card dashboard-page-chart-card">
							<div class="dashboard-page-chart-title">Проданные товары по месяцам, кг</div>
							<div data-chart="kg_trend"></div>
						</div>
						<div class="dashboard-page-card">
							<div class="dashboard-page-table-slot" data-table="regional-summary"></div>
						</div>
					</div>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "page-dashboard",
		});

		this.$tabs = this.page.main.find('[data-region="tabs"]');
		this.$kpis = this.page.main.find('[data-region="kpis"]');
		this.$years = this.page.main.find('[data-region="years"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.page_dashboard.page_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.selectedYear = String(this.context.default_year || this.selectedYear || "");
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
		const totals = (this.context.kpi_totals_by_year || {})[this.selectedYear] || {};
		this.$kpis.html(
			kpis
				.map(
					(kpi) => `
						<div class="dashboard-page-card dashboard-page-kpi-card">
							<div class="dashboard-page-kpi-number">${frappe.utils.escape_html(totals[kpi.key] || "0")}</div>
							<div class="dashboard-page-kpi-label">${frappe.utils.escape_html(kpi.label)}</div>
							${kpi.subtext ? `<div class="dashboard-page-kpi-subtext">${frappe.utils.escape_html(kpi.subtext)}</div>` : ""}
						</div>
					`
				)
				.join("")
		);
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
				.join("") + '<div class="dashboard-page-year-spinner"></div>'
		);

		this.$years.find(".dashboard-page-year").on("click", (e) => {
			this.selectedYear = String($(e.currentTarget).data("year"));
			this.render_year_buttons();
			this.render_kpis();
			this.render_tables();
			this.render_charts();
		});
	}

	render_tables() {
		this.render_table(
			"sales-by-month",
			((this.context.sales_by_month_by_year || {})[this.selectedYear]) || [],
			["Месяц", "Сум прод"],
			"Продажа"
		);
		this.render_table(
			"returns-by-month",
			((this.context.returns_by_month_by_year || {})[this.selectedYear]) || [],
			["Месяц", "Возврат"],
			"Возврат"
		);
		this.render_table(
			"product-margin",
			(this.context.product_margin_by_year || {})[this.selectedYear] || [],
			["Товары", "Маржа", "Рен"]
		);
		this.render_table(
			"client-kpi",
			((this.context.client_kpi_by_year || {})[this.selectedYear]) || [],
			["Клиент", "КГ", "Сумма продаж", "Рен"]
		);
		this.render_table(
			"regional-summary",
			((this.context.regional_summary_by_year || {})[this.selectedYear]) || [],
			["Город", "Сумма", "Маржа", "Рен"]
		);
	}

	render_table(key, rows, headers, title = null) {
		const $slot = this.page.main.find(`[data-table="${key}"]`);
		$slot.html(`
			${title ? `<div class="dashboard-page-table-title">${frappe.utils.escape_html(title)}</div>` : ""}
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
											const rawValue = String(value ?? "");
											const cellValue = key === "client-kpi" && index === 0 ? this.shorten_label(rawValue, 22) : rawValue;
											const titleAttr =
												key === "client-kpi" && index === 0
													? ` title="${frappe.utils.escape_html(rawValue)}"`
													: "";
											return `<td class="${alignClass}"${titleAttr}>${frappe.utils.escape_html(cellValue)}</td>`;
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

	shorten_label(value, maxLength = 22) {
		if (!value || value.length <= maxLength) {
			return value;
		}

		return `${value.slice(0, Math.max(maxLength - 1, 1)).trimEnd()}…`;
	}

	render_charts() {
		const yearCharts = (this.context.chart_data_by_year || {})[this.selectedYear] || {};
		Object.entries(this.charts).forEach(([key, meta]) => {
			const $container = this.page.main.find(`[data-chart="${key}"]`);
			this.render_chart_panel($container, yearCharts[key] || { labels: [], datasets: [{ values: [] }] }, meta);
		});
	}

	render_chart_panel($container, chartData, meta) {
		const labels = chartData.labels || [];
		const values = ((chartData.datasets || [])[0] || {}).values || [];
		const maxValue = values.length ? Math.max(...values, 0) : 0;
		const totalValue = keyTotals(meta.totalLabel, values);

		$container.html(`
			<div class="dashboard-page-mini-chart">
				<div class="dashboard-page-mini-chart-head">
					<div class="is-month">${__("Месяц")}</div>
					<div class="is-value">${frappe.utils.escape_html(meta.valueLabel)}</div>
					<div class="is-bar"></div>
				</div>
				<div class="dashboard-page-mini-chart-body">
					${labels
						.map((label, index) => {
							const value = Number(values[index] || 0);
							const width = maxValue ? Math.max((value / maxValue) * 100, 4) : 0;
							return `
								<div class="dashboard-page-mini-chart-row">
									<div class="is-month">${frappe.utils.escape_html(label)}</div>
									<div class="is-value">${frappe.utils.escape_html(this.formatInteger(value))}</div>
									<div class="is-bar">
										<div class="dashboard-page-mini-chart-bar" style="width:${width}%"></div>
									</div>
								</div>
							`;
						})
						.join("")}
				</div>
				<div class="dashboard-page-mini-chart-total">
					<div class="is-month">${frappe.utils.escape_html(meta.totalLabel)}</div>
					<div class="is-value">${frappe.utils.escape_html(this.formatInteger(totalValue))}</div>
					<div class="is-bar"></div>
				</div>
			</div>
		`);

		function keyTotals(totalLabel, valuesList) {
			if (totalLabel === "Макс") {
				return valuesList.length ? Math.max(...valuesList, 0) : 0;
			}
			return valuesList.reduce((sum, value) => sum + Number(value || 0), 0);
		}
	}

	formatInteger(value) {
		const sign = value < 0 ? "-" : "";
		const numeric = Math.abs(Math.round(Number(value || 0)));
		return `${sign}${String(numeric).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}`;
	}

};
