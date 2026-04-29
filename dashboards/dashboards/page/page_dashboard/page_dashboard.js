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
		this.metricColumns = {
			check_trend: { label: "Средний чек", totalLabel: "Макс" },
			price_trend: { label: "Средняя себестоимость", totalLabel: "Макс" },
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
						<div class="dashboard-page-card dashboard-page-chart-card dashboard-page-chart-card--wide">
							<div class="dashboard-page-chart-title">Динамика по месяцам</div>
							<div data-chart="combined-month-metrics"></div>
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
		const columnWidths = this.getTableColumnWidths(key, headers.length);
		$slot.html(`
			${title ? `<div class="dashboard-page-table-title">${frappe.utils.escape_html(title)}</div>` : ""}
			<table class="dashboard-page-table">
				<colgroup>
					${columnWidths.map((width) => `<col style="width:${width}">`).join("")}
				</colgroup>
				<thead>
					<tr>
						${headers
							.map((header, index) => {
								const alignClass = index === 0 ? "is-text" : "is-number";
								return `<th class="${alignClass}">${frappe.utils.escape_html(header)}</th>`;
							})
							.join("")}
					</tr>
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

	getTableColumnWidths(key, columnCount) {
		const widthMap = {
			"sales-by-month": ["48%", "52%"],
			"returns-by-month": ["48%", "52%"],
			"product-margin": ["48%", "32%", "20%"],
			"client-kpi": ["34%", "16%", "32%", "18%"],
			"regional-summary": ["34%", "22%", "26%", "18%"],
		};

		return widthMap[key] || Array.from({ length: columnCount }, () => `${100 / Math.max(columnCount, 1)}%`);
	}

	shorten_label(value, maxLength = 22) {
		if (!value || value.length <= maxLength) {
			return value;
		}

		return `${value.slice(0, Math.max(maxLength - 1, 1)).trimEnd()}…`;
	}

	render_charts() {
		const yearCharts = (this.context.chart_data_by_year || {})[this.selectedYear] || {};
		const $container = this.page.main.find('[data-chart="combined-month-metrics"]');
		this.render_combined_chart_panel($container, yearCharts);
	}

	render_combined_chart_panel($container, yearCharts) {
		const monthLabels =
			(yearCharts.price_trend && yearCharts.price_trend.labels) ||
			(yearCharts.check_trend && yearCharts.check_trend.labels) ||
			(yearCharts.kg_trend && yearCharts.kg_trend.labels) ||
			[];
		const rows = monthLabels.map((label, index) => {
			const metrics = {};
			Object.entries(this.metricColumns).forEach(([key, meta]) => {
				const values = ((((yearCharts[key] || {}).datasets || [])[0] || {}).values) || [];
				const value = Number(values[index] || 0);
				metrics[key] = {
					value,
					label: meta.label,
				};
			});
			return { label, metrics };
		});
		const totals = {};
		Object.entries(this.metricColumns).forEach(([key, meta]) => {
			const values = ((((yearCharts[key] || {}).datasets || [])[0] || {}).values) || [];
			totals[key] = this.getMetricTotal(meta.totalLabel, values);
		});

		$container.html(`
			<div class="dashboard-page-month-metrics">
				<div class="dashboard-page-month-metrics-head">
					<div class="is-month">${__("Месяц")}</div>
					<div class="is-metric">${frappe.utils.escape_html(this.metricColumns.check_trend.label)}</div>
					<div class="is-metric">${frappe.utils.escape_html(this.metricColumns.price_trend.label)}</div>
					<div class="is-metric">${frappe.utils.escape_html("Фарқ")}</div>
				</div>
				<div class="dashboard-page-month-metrics-body">
					${rows
						.map(
							(row) => {
								const difference = row.metrics.check_trend.value - row.metrics.price_trend.value;
								return `
								<div class="dashboard-page-month-metrics-row">
									<div class="is-month">${frappe.utils.escape_html(row.label)}</div>
									<div class="is-metric">${frappe.utils.escape_html(this.formatInteger(row.metrics.check_trend.value))}</div>
									<div class="is-metric">${frappe.utils.escape_html(this.formatInteger(row.metrics.price_trend.value))}</div>
									<div class="is-metric">${frappe.utils.escape_html(this.formatInteger(difference))}</div>
								</div>
							`;
							}
						)
						.join("")}
				</div>
				<div class="dashboard-page-month-metrics-total">
					<div class="is-month">${__("Итог")}</div>
					<div class="is-metric">
						<div class="dashboard-page-month-metrics-total-label">${frappe.utils.escape_html(this.metricColumns.check_trend.totalLabel)}</div>
						<div>${frappe.utils.escape_html(this.formatInteger(totals.check_trend))}</div>
					</div>
					<div class="is-metric">
						<div class="dashboard-page-month-metrics-total-label">${frappe.utils.escape_html(this.metricColumns.price_trend.totalLabel)}</div>
						<div>${frappe.utils.escape_html(this.formatInteger(totals.price_trend))}</div>
					</div>
					<div class="is-metric">
						<div class="dashboard-page-month-metrics-total-label">${frappe.utils.escape_html("Фарқ")}</div>
						<div>${frappe.utils.escape_html(this.formatInteger(totals.check_trend - totals.price_trend))}</div>
					</div>
				</div>
			</div>
		`);
	}

	getMetricTotal(totalLabel, valuesList) {
		if (totalLabel === "Макс") {
			return valuesList.length ? Math.max(...valuesList, 0) : 0;
		}
		return valuesList.reduce((sum, value) => sum + Number(value || 0), 0);
	}

	formatInteger(value) {
		const sign = value < 0 ? "-" : "";
		const numeric = Math.abs(Math.round(Number(value || 0)));
		return `${sign}${String(numeric).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}`;
	}

};
