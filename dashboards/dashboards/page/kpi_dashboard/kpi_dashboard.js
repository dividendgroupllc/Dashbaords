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
		this.selectedYear = null;
		this.selectedMonth = null;
		this.kpiMeta = [
			["sales", "Продажа", "Общий объем продаж за период"],
			["margin", "Маржа", "Продажа минус себестоимость"],
			["margin_minus_discount", "Маржа-Бонус-Скидка", "Чистая маржа после скидок"],
			["returns", "Возврат", "Сумма возвратов клиентов"],
			["bonus", "Бонус", "Лояльность и бесплатные позиции"],
			["discount", "Скидка", "Сумма скидок по строкам"],
		];

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
					<div class="kpi-dashboard-brand">
						<div class="kpi-dashboard-logo">KP</div>
						<div class="kpi-dashboard-brand-copy">
							<div class="kpi-dashboard-brand-title">2 Информационная Панель</div>
							<div class="kpi-dashboard-brand-subtitle">Компания</div>
						</div>
					</div>
					<div class="kpi-dashboard-title">KPI</div>
					<div class="kpi-dashboard-header-info">i</div>
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
						<div class="kpi-dashboard-caption" data-region="caption"></div>
						<div class="kpi-dashboard-card">
							<div class="kpi-dashboard-table-wrap" data-region="client-table"></div>
						</div>
						<div class="kpi-dashboard-bottom">
							<div class="kpi-dashboard-card">
								<div class="kpi-dashboard-subtitle">Клиент</div>
								<div class="kpi-dashboard-table-wrap" data-region="summary-table"></div>
							</div>
							<div class="kpi-dashboard-card">
								<div class="kpi-dashboard-subtitle">Диаграмма клиента</div>
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
		this.$caption = this.page.main.find('[data-region="caption"]');
		this.$clientTable = this.page.main.find('[data-region="client-table"]');
		this.$summaryTable = this.page.main.find('[data-region="summary-table"]');
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
		this.render_caption();
		this.render_client_table();
		this.render_summary_table();
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
			this.selectedMonth = null;
			this.load_data();
		});
	}

	render_months() {
		this.$months.html(
			(this.data.months || [])
				.map(
					(month) => `
						<button class="kpi-dashboard-month ${month === this.selectedMonth ? "is-active" : ""}" data-month="${month}">
							<span class="kpi-dashboard-month-mark"></span>
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
		const totals = this.data.kpi_totals || {};
		this.$kpis.html(
			this.kpiMeta
				.map(
					([key, label, subtext]) => `
						<div class="kpi-dashboard-card kpi-dashboard-kpi-card">
							<div class="kpi-dashboard-kpi-value">${frappe.utils.escape_html(totals[key] || "0")}</div>
							<div class="kpi-dashboard-kpi-label">${frappe.utils.escape_html(label)}</div>
							<div class="kpi-dashboard-kpi-subtext">${frappe.utils.escape_html(subtext)}</div>
						</div>
					`
				)
				.join("")
		);
	}

	render_caption() {
		this.$caption.text(
			`${this.selectedMonth || ""} ${this.selectedYear || ""} kesimidagi KPI ko'rsatkichlari mijozlar kesimida dinamik ravishda bazadan yuklandi.`
		);
	}

	render_client_table() {
		const headers = ["Клиент", "Продажа", "Сб.ст", "КГ", "Возврат", "Маржа", "%", "Бонус", "Скидка", "Маржа нет", "PnL"];
		this.$clientTable.html(this.make_table(headers, this.data.client_rows || [], "wide"));
	}

	render_summary_table() {
		const headers = ["Клиент", "Продажа", "%", "Маржа", "Бонус", "Скидка"];
		this.$summaryTable.html(this.make_table(headers, this.data.summary_rows || [], "compact"));
	}

	make_table(headers, rows, variant) {
		const widths = this.get_column_widths(variant, headers.length);
		const colgroup = widths.length
			? `<colgroup>${widths.map((width) => `<col style="width:${width}">`).join("")}</colgroup>`
			: "";
		return `
			<table class="kpi-dashboard-table kpi-dashboard-table--${variant}">
				${colgroup}
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

	get_column_widths(variant, length) {
		if (variant === "wide") {
			return ["18%", "9%", "9%", "7%", "9%", "9%", "6%", "9%", "8%", "10%", "6%"];
		}

		if (variant === "compact") {
			return ["28%", "16%", "10%", "16%", "15%", "15%"];
		}

		return new Array(length).fill(`${Math.floor(100 / Math.max(length, 1))}%`);
	}

	render_treemap() {
		const items = this.data.treemap || [];
		const total = items.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1;
		const palette = ["#2f87e4", "#2836a7", "#f07432", "#7a0f93", "#d63ba6", "#7251c7", "#f0c000", "#20a36e"];
		const formatNumber = (value) => new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Number(value || 0));

		this.$treemap.html(
			items
				.map((item, index) => {
					const ratio = Math.max(10, Math.round((Number(item.value || 0) / total) * 100));
					return `
						<div class="kpi-dashboard-treemap-item" style="flex:${ratio}; background:${palette[index % palette.length]}">
							<div class="kpi-dashboard-treemap-name">${frappe.utils.escape_html(item.label)}</div>
							<div class="kpi-dashboard-treemap-value">${frappe.utils.escape_html(formatNumber(item.value))}</div>
						</div>
					`;
				})
				.join("")
		);
	}
};
