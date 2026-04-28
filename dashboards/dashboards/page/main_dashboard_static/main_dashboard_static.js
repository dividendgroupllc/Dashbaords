frappe.pages["main-dashboard-static"].on_page_load = function (wrapper) {
	new dashboards.ui.MainDashboardStaticPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.MainDashboardStaticPage = class MainDashboardStaticPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Main Dashboard"),
			single_column: true,
		});

		this.state = {
			year: "",
			month: "",
		};
		this.months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
		this.years = [];
		this.data = null;

		this.make_layout();
		this.bind_events();
		this.load_data();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("main-dashboard-static-layout");
		this.wrapper.find(".page-head").addClass("main-dashboard-static-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="mds-screen">
				<section class="mds-main">
					<div class="mds-filters">
						<div class="mds-filter-label">YEAR FILTER</div>
						<div class="mds-year-select">
							<button class="mds-select" type="button" data-year-toggle aria-expanded="false">
								<span data-region="selected-year">...</span>
								<span class="mds-chevron"></span>
							</button>
							<div class="mds-year-menu" data-region="year-menu"></div>
						</div>
						<div class="mds-filter-label">MONTH FILTER</div>
						<div class="mds-month-grid" data-region="month-grid"></div>
					</div>
					<div class="mds-content">
						<section class="mds-card mds-card--wide mds-sales-card">
							<div class="mds-card-head">
								<h2>SALES VOLUME (TONS)</h2>
							</div>
							<div class="mds-bar-chart" data-region="sales-chart"></div>
						</section>
						<section class="mds-card mds-card--donut">
							<div class="mds-card-head">
								<h2>MARGIN & BONUS</h2>
							</div>
							<div data-region="margin-bonus"></div>
						</section>
						<section class="mds-card mds-average-card">
							<div data-region="average-check"></div>
						</section>
						<section class="mds-card mds-balance-card">
							<div data-region="balance-details"></div>
						</section>
						<section class="mds-card mds-break-card">
							<div data-region="unit-cost"></div>
						</section>
						<section class="mds-card mds-returns-card">
							<h2>RETURNS ANALYSIS</h2>
							<div class="mds-return-chart" data-region="return-chart"></div>
						</section>
						<section class="mds-card mds-profit-card">
							<div class="mds-card-head">
								<h2>NET PROFIT & PROFITABILITY</h2>
								<div class="mds-legend mds-legend--compact">
									<span><i class="is-blue"></i> Net Profit</span>
									<span><i class="is-green"></i> Profitability</span>
								</div>
							</div>
							<div class="mds-profit-chart" data-region="profit-chart"></div>
						</section>
					</div>
				</section>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "main-dashboard-static",
		});

		this.$salesChart = this.page.main.find('[data-region="sales-chart"]');
		this.$returnChart = this.page.main.find('[data-region="return-chart"]');
		this.$profitChart = this.page.main.find('[data-region="profit-chart"]');
		this.$selectedYear = this.page.main.find('[data-region="selected-year"]');
		this.$yearMenu = this.page.main.find('[data-region="year-menu"]');
		this.$monthGrid = this.page.main.find('[data-region="month-grid"]');
		this.$marginBonus = this.page.main.find('[data-region="margin-bonus"]');
		this.$averageCheck = this.page.main.find('[data-region="average-check"]');
		this.$balanceDetails = this.page.main.find('[data-region="balance-details"]');
		this.$unitCost = this.page.main.find('[data-region="unit-cost"]');
	}

	bind_events() {
		this.page.main.off(".main-dashboard-static");

		this.page.main.on("click.main-dashboard-static", "[data-year-toggle]", (event) => {
			event.stopPropagation();
			const $select = $(event.currentTarget).closest(".mds-year-select");
			const isOpen = $select.hasClass("is-open");
			$select.toggleClass("is-open", !isOpen);
			$(event.currentTarget).attr("aria-expanded", isOpen ? "false" : "true");
		});

		this.page.main.on("click.main-dashboard-static", "[data-year]", (event) => {
			const year = String($(event.currentTarget).data("year"));
			this.load_data({ year, month: this.state.month });
		});

		this.page.main.on("click.main-dashboard-static", "[data-month]", (event) => {
			const month = String($(event.currentTarget).data("month"));
			this.load_data({ year: this.state.year, month });
		});

		this.page.main.on("click.main-dashboard-static", "[data-balance-toggle]", (event) => {
			const $item = $(event.currentTarget).closest(".mds-balance-item");
			const isOpen = $item.hasClass("is-open");
			$item.toggleClass("is-open", !isOpen);
			$(event.currentTarget).attr("aria-expanded", isOpen ? "false" : "true");
		});

		$(document).off("click.main-dashboard-static-year").on("click.main-dashboard-static-year", (event) => {
			if ($(event.target).closest(".mds-year-select").length) {
				return;
			}

			this.page.main.find(".mds-year-select").removeClass("is-open");
			this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
		});
	}

	render_year_option(year) {
		return `<button class="mds-year-option ${year === this.state.year ? "is-active" : ""}" type="button" data-year="${year}">${year}</button>`;
	}

	render_month_button(month) {
		return `<button class="mds-month ${month === this.state.month ? "is-active" : ""}" type="button" data-month="${month}">${month}</button>`;
	}

	render_balance_item(label, value, details = [], open = false) {
		return `
			<div class="mds-balance-item ${open ? "is-open" : ""}">
				<button class="mds-balance-row" type="button" data-balance-toggle aria-expanded="${open ? "true" : "false"}">
					<span class="mds-chevron"></span>
					<span>${frappe.utils.escape_html(label)}</span>
					<strong>${frappe.utils.escape_html(value)}</strong>
				</button>
				<div class="mds-balance-detail">
					${details
						.map(
							([detailLabel, detailValue]) => `
								<div class="mds-balance-sub">
									<span>${frappe.utils.escape_html(detailLabel)}</span>
									<strong>${frappe.utils.escape_html(detailValue)}</strong>
								</div>
							`
						)
						.join("")}
				</div>
			</div>
		`;
	}

	load_data(filters = {}) {
		this.show_loading();
		return frappe.call({
			method: "dashboards.dashboards.page.main_dashboard_static.main_dashboard_static.get_dashboard_data",
			args: {
				year: filters.year || this.state.year || undefined,
				month: filters.month || this.state.month || undefined,
			},
		}).then((response) => {
			this.data = response.message || {};
			const backendFilters = this.data.filters || {};
			this.years = backendFilters.years || [];
			this.state.year = backendFilters.selected_year || "";
			this.state.month = backendFilters.selected_month || "";
			this.render();
		}).catch(() => {
			frappe.msgprint(__("Main Dashboard data could not be loaded."));
		});
	}

	show_loading() {
		const loadingMarkup = `<div class="mds-loading">Loading...</div>`;
		this.$salesChart.html(loadingMarkup);
		this.$returnChart.html(loadingMarkup);
		this.$profitChart.html(loadingMarkup);
		this.$marginBonus.html(loadingMarkup);
		this.$averageCheck.html(loadingMarkup);
		this.$balanceDetails.html(loadingMarkup);
		this.$unitCost.html(loadingMarkup);
	}

	render() {
		this.render_filters();
		this.render_sales_chart();
		this.render_returns_chart();
		this.render_margin_bonus();
		this.render_average_check();
		this.render_balance_details();
		this.render_unit_cost();
		this.render_profit_chart();
	}

	render_filters() {
		this.$selectedYear.text(this.state.year || "...");
		this.$yearMenu.html(this.years.map((year) => this.render_year_option(year)).join(""));
		this.$monthGrid.html(this.months.map((month) => this.render_month_button(month)).join(""));
	}

	render_sales_chart() {
		const salesData = this.data?.sales_volume?.series || [];
		const maxSales = Math.max(1, ...salesData.map((row) => Number(row.tons || 0)));
		this.$salesChart.html(`
			<div class="mds-bar-grid">
				${this.months
					.map((month, index) => {
						const row = salesData[index] || { tons: 0, amount_display: "" };
						return this.render_chart_bar({
							month,
							row,
							maxValue: maxSales,
							active: month === this.state.month,
							barClass: "mds-bar",
						});
					})
					.join("")}
			</div>
		`);
	}

	render_returns_chart() {
		const returnData = this.data?.returns_analysis?.series || [];
		const maxReturns = Math.max(1, ...returnData.map((row) => Number(row.tons || 0)));
		this.$returnChart.html(`
			<div class="mds-return-grid">
				${this.months
					.map((month, index) => {
						const row = returnData[index] || { tons: 0, amount_display: "" };
						return this.render_chart_bar({
							month,
							row,
							maxValue: maxReturns,
							active: month === this.state.month,
							barClass: "mds-return-bar",
						});
					})
					.join("")}
			</div>
		`);
	}

	render_chart_bar({ month, row, maxValue, active, barClass }) {
		const tons = Number(row.tons || 0);
		const height = maxValue > 0 && tons > 0 ? Math.max((tons / maxValue) * 100, 12) : 0;

		return `
			<div class="mds-bar-item ${active ? "is-active" : ""}">
				<div class="mds-bar-ton">${row.tons_display || ""}</div>
				<div class="mds-bar-shell">
					<div class="${barClass} ${active ? "is-active" : ""} ${tons ? "" : "is-empty"}" style="height:${height}%">
						${row.amount_display ? `<span class="mds-bar-amount">${frappe.utils.escape_html(row.amount_display)}</span>` : ""}
					</div>
				</div>
				<span class="mds-bar-month">${frappe.utils.escape_html(month)}</span>
			</div>
		`;
	}

	render_margin_bonus() {
		const data = this.data?.margin_bonus || {};
		const bonusPercent = Number(data.bonus_percent || 0);
		this.$marginBonus.html(`
			<div class="mds-donut-wrap">
				<div class="mds-donut" style="background: conic-gradient(var(--mds-mint) 0 ${bonusPercent}%, var(--mds-blue) ${bonusPercent}% 100%);">
					<div class="mds-donut-core">
						<strong>${frappe.utils.escape_html(data.center_value || "0%")}</strong>
						<span>${frappe.utils.escape_html(data.center_label || "Margin")}</span>
					</div>
				</div>
			</div>
			<div class="mds-legend">
				<span><i class="is-blue"></i> ${frappe.utils.escape_html(data.margin_display || "Margin (0%)")}</span>
				<span><i class="is-mint"></i> ${frappe.utils.escape_html(data.bonus_display || "Bonus (0%)")}</span>
			</div>
		`);
	}

	render_delta_badge(value, valueDisplay) {
		const cssClass = Number(value || 0) >= 0 ? "is-up" : "is-down";
		return `<em class="${cssClass}">${frappe.utils.escape_html(valueDisplay || "0.0%")}</em>`;
	}

	render_average_check() {
		const data = this.data?.average_check || {};
		const healthRatio = Number(data.health_ratio || 0);
		const healthRatioCapped = Math.max(0, Math.min(100, Number(data.health_ratio_capped || 0)));
		this.$averageCheck.html(`
			<h2>AVERAGE CHECK</h2>
			<div class="mds-price-row">
				<div>
					<span>Selling Price</span>
					<strong>${frappe.utils.escape_html(data.selling_price_display || "0 UZS")}</strong>
				</div>
				${this.render_delta_badge(data.selling_change, data.selling_change_display)}
			</div>
			<div class="mds-price-row">
				<div>
					<span>Cost Price</span>
					<strong class="is-muted">${frappe.utils.escape_html(data.cost_price_display || "0 UZS")}</strong>
				</div>
				${this.render_delta_badge(data.cost_change, data.cost_change_display)}
			</div>
			<div class="mds-health-card">
				<div class="mds-health-head">
					<div>
						<span>Business Health</span>
						<strong>${frappe.utils.escape_html(data.health_ratio_display || "0.0%")}</strong>
					</div>
					<em class="${healthRatio <= 30 ? "is-good" : healthRatio <= 50 ? "is-warn" : "is-risk"}">
						Qarz / Savdo
					</em>
				</div>
				<div class="mds-health-bar">
					<div class="mds-health-scale"></div>
					<div class="mds-health-pointer" style="left: ${healthRatioCapped}%;"></div>
				</div>
				<div class="mds-health-ticks">
					<span>0%</span>
					<span>30%</span>
					<span>50%</span>
					<span>100%</span>
				</div>
				<div class="mds-health-meta">
					<div>
						<span>Qarz</span>
						<strong>${frappe.utils.escape_html(data.health_debt_display || "0 UZS")}</strong>
					</div>
					<div>
						<span>Savdo</span>
						<strong>${frappe.utils.escape_html(data.health_sales_display || "0 UZS")}</strong>
					</div>
				</div>
			</div>
		`);
	}

	render_balance_details() {
		const data = this.data?.balance_details || {};
		const items = data.items || [];
		this.$balanceDetails.html(`
			<h2>BALANCE DETAILS</h2>
			${items
				.map((item) => this.render_balance_item(item.label, item.value, item.details || [], Boolean(item.open)))
				.join("")}
			<div class="mds-total-balance">
				<span>TOTAL BALANCE</span>
				<strong>${frappe.utils.escape_html(data.total_balance || "0 UZS")}</strong>
			</div>
		`);
	}

	render_unit_cost() {
		const breakEven = this.data?.break_even || {};
		const data = this.data?.unit_cost || {};
		const planRatio = Math.max(0, Math.min(100, Number(breakEven.plan_ratio || 0)));
		const currentRatio = Math.max(planRatio, Math.min(100, Number(breakEven.current_ratio || 0)));
		const greenWidth = Math.max(currentRatio - planRatio, 0);
		this.$unitCost.html(`
			<h2>BREAK-EVEN</h2>
			<div class="mds-progress-head">
				<span class="mds-progress-title">${frappe.utils.escape_html(breakEven.title || "Production Progress")}</span>
				<strong class="mds-progress-summary">${frappe.utils.escape_html(breakEven.summary || "0t / 0t")}</strong>
			</div>
			<div class="mds-progress" style="--mds-plan-ratio:${planRatio}%; --mds-current-ratio:${currentRatio}%; --mds-green-width:${greenWidth}%;">
				<div class="mds-progress-line mds-progress-line--red"></div>
				<div class="mds-progress-line mds-progress-line--green"></div>
				<span class="mds-progress-dot mds-progress-dot--start"></span>
				<span class="mds-progress-dot mds-progress-dot--plan"></span>
				<span class="mds-progress-dot mds-progress-dot--current"></span>
			</div>
			<div class="mds-progress-scale">
				<span class="mds-progress-badge mds-progress-badge--start">${frappe.utils.escape_html(breakEven.start_label || "0t")}</span>
				<span class="mds-progress-badge mds-progress-badge--plan">${frappe.utils.escape_html(breakEven.plan_label || "Plan: 0t")}</span>
				<span class="mds-progress-badge mds-progress-badge--current">${frappe.utils.escape_html(breakEven.current_label || "Current: 0t")}</span>
			</div>
			<div class="mds-unit-card">
				<div class="mds-unit-card-head">
					<span class="mds-unit-period">${frappe.utils.escape_html(data.period_label || "-")}</span>
					<strong>${frappe.utils.escape_html(data.title || "1 kg kolbasa uchun xarajat")}</strong>
				</div>
				<div class="mds-unit-value">${frappe.utils.escape_html(data.unit_cost_display || "0.00 UZS")}</div>
				<div class="mds-unit-formula">${frappe.utils.escape_html(data.formula_label || "Xarajat / kg")}</div>
				<div class="mds-unit-stats">
					<div class="mds-unit-stat">
						<span>Jami xarajat</span>
						<strong>${frappe.utils.escape_html(data.production_cost_display || "0.00 UZS")}</strong>
					</div>
					<div class="mds-unit-stat">
						<span>Ishlab chiqarilgan</span>
						<strong>${frappe.utils.escape_html(data.manufactured_qty_display || "0.00 kg")}</strong>
					</div>
				</div>
			</div>
		`);
	}

	render_profit_chart() {
		const profitData = this.data?.net_profit_profitability?.series || [];
		const maxProfitValue = Math.max(100, ...profitData.map((row) => Number(row.profit || 0)));
		const maxProfitabilityValue = Math.max(10, ...profitData.map((row) => Number(row.profitability || 0)));
		const axisPadding = Math.max(maxProfitValue * 0.2, 10);
		const axisTop = Math.ceil((maxProfitValue + axisPadding) / 10) * 10;
		const axisValues = [axisTop, axisTop * (2 / 3), axisTop * (1 / 3), 0];
		const formatAxisValue = (value) => {
			if (!value) {
				return "0 K";
			}

			const absoluteAmount = value * 1000;
			if (Math.abs(absoluteAmount) >= 1000000) {
				const millions = absoluteAmount / 1000000;
				const roundedMillions = Math.abs(millions) >= 10 ? Math.round(millions) : Number(millions.toFixed(1));
				return `${roundedMillions} M`;
			}

			const roundedThousands = value >= 10 ? Math.round(value) : Number(value.toFixed(1));
			return `${roundedThousands} K`;
		};
		this.$profitChart.html(`
			<div class="mds-profit-plot">
				<div class="mds-profit-axis">
					${axisValues
						.map(
							(value) => `
								<div class="mds-profit-axis-row">
									<span class="mds-profit-axis-label">${formatAxisValue(value)}</span>
									<span class="mds-profit-axis-line"></span>
								</div>
							`
						)
						.join("")}
				</div>
				<div class="mds-profit-bars" style="grid-template-columns: repeat(${profitData.length || 1}, minmax(72px, 1fr));">
					${profitData
						.map((row) => {
							const profitValue = Number(row.profit || 0);
							const profitabilityValue = Number(row.profitability || 0);
							const profitHeight = profitValue ? Math.max((profitValue / axisTop) * 100, 3) : 0;
							const profitabilityHeight = profitabilityValue ? Math.max((profitabilityValue / maxProfitabilityValue) * 100, 3) : 0;
							return `
								<div class="mds-profit-group">
									<div class="mds-profit-columns">
										<div class="mds-profit-bar-wrap">
											<span class="mds-profit-value mds-profit-value--blue">${frappe.utils.escape_html(row.profit_display || "0K")}</span>
											<div class="mds-profit-bar mds-profit-bar--blue ${profitValue ? "" : "is-zero"}" style="height:${profitHeight}%; width: 10px;"></div>
										</div>
										<div class="mds-profit-bar-wrap">
											<span class="mds-profit-value mds-profit-value--green">${frappe.utils.escape_html(row.profitability_display || "0.0%")}</span>
											<div class="mds-profit-bar mds-profit-bar--green ${profitabilityValue ? "" : "is-zero"}" style="height:${profitabilityHeight}%; width: 10px;"></div>
										</div>
									</div>
									<span class="mds-profit-month">${frappe.utils.escape_html(row.month)}</span>
								</div>
							`;
						})
						.join("")}
				</div>
			</div>
		`);
	}
};
