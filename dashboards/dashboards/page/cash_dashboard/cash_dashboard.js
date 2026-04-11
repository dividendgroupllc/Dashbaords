frappe.pages["cash-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.CashDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.CashDashboardPage = class CashDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Cash Dashboard"),
			single_column: true,
		});

		this.state = {
			month: null,
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("cash-dashboard-layout");
		this.wrapper.find(".page-head").addClass("cash-dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="cash-dashboard-screen">
				<div class="cash-dashboard-shell">
					<div class="cash-dashboard-tabs" data-region="tabs"></div>
					<div class="cash-dashboard-months" data-region="months"></div>
					<div class="cash-dashboard-kpis">
						<div class="cash-dashboard-kpi cash-dashboard-kpi--wide" data-region="cash-kpi"></div>
						<div class="cash-dashboard-kpi cash-dashboard-kpi--balance" data-region="cash-balance"></div>
						<div class="cash-dashboard-kpi cash-dashboard-kpi--balance" data-region="bank-balance"></div>
						<div class="cash-dashboard-kpi cash-dashboard-kpi--wide" data-region="bank-kpi"></div>
					</div>
					<div class="cash-dashboard-content">
						<div class="cash-dashboard-table-slot" data-region="cash-table"></div>
						<div class="cash-dashboard-table-slot" data-region="bank-table"></div>
					</div>
				</div>
			</div>
		`);

		this.$tabs = this.page.main.find('[data-region="tabs"]');
		this.$months = this.page.main.find('[data-region="months"]');
		this.$cashKpi = this.page.main.find('[data-region="cash-kpi"]');
		this.$cashBalance = this.page.main.find('[data-region="cash-balance"]');
		this.$bankBalance = this.page.main.find('[data-region="bank-balance"]');
		this.$bankKpi = this.page.main.find('[data-region="bank-kpi"]');
		this.$cashTable = this.page.main.find('[data-region="cash-table"]');
		this.$bankTable = this.page.main.find('[data-region="bank-table"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.cash_dashboard.cash_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.state = { ...(this.context.default_filters || {}) };
				this.render();
			},
		});
	}

	render() {
		this.render_tabs();
		this.render_months();
		this.render_kpis();
		this.render_tables();
	}

	render_tabs() {
		const tabs = this.context.tabs || [];
		this.$tabs.html(
			tabs
				.map(
					(tab) => `
						<button class="cash-dashboard-tab ${tab.active ? "is-active" : ""}" data-route="${tab.route}">
							${frappe.utils.escape_html(tab.label)}
						</button>
					`
				)
				.join("") +
				`<div class="cash-dashboard-info">i</div>`
		);

		this.$tabs.find("[data-route]").on("click", (e) => {
			const route = $(e.currentTarget).data("route");
			if (route) {
				frappe.set_route(route.replace(/^\/app\//, ""));
			}
		});
	}

	render_months() {
		const months = this.context.months || [];
		this.$months.html(
			months
				.map(
					(month) => `
						<button class="cash-dashboard-month ${month.key === this.state.month ? "is-active" : ""}" data-month="${month.key}">
							${frappe.utils.escape_html(month.label)}
						</button>
					`
				)
				.join("")
		);

		this.$months.find("[data-month]").on("click", (e) => {
			this.state.month = String($(e.currentTarget).data("month"));
			this.render_kpis();
			this.render_tables();
			this.render_months();
		});
	}

	render_kpis() {
		const metrics = this.getMetrics();

		this.$cashKpi.html(this.getWideKpiMarkup(metrics.cash, "касса"));
		this.$bankKpi.html(this.getWideKpiMarkup(metrics.bank, "банк"));
		this.$cashBalance.html(this.getBalanceMarkup(metrics.cash.end, "Остаток касса"));
		this.$bankBalance.html(this.getBalanceMarkup(metrics.bank.end, "Остаток банк"));
	}

	render_tables() {
		const metrics = this.getMetrics();
		const cashRows = this.getRowsForMonth(this.context.cash_rows || [], metrics.cash.inflow, "cash");
		const bankRows = this.getRowsForMonth(this.context.bank_rows || [], metrics.bank.inflow, "bank");
		this.$cashTable.html(this.getTableMarkup(cashRows, metrics.cash, "касса"));
		this.$bankTable.html(this.getTableMarkup(bankRows, metrics.bank, "банк"));
	}

	getWideKpiMarkup(metric, label) {
		return `
			<div class="cash-dashboard-kpi-grid">
				<div class="cash-dashboard-kpi-item">
					<div class="cash-dashboard-kpi-value is-green">${this.formatInteger(metric.start)}</div>
					<div class="cash-dashboard-kpi-label">Начало ${label}</div>
				</div>
				<div class="cash-dashboard-kpi-item">
					<div class="cash-dashboard-kpi-value is-green">${this.formatInteger(metric.inflow)}</div>
					<div class="cash-dashboard-kpi-label">Приход ${label}</div>
				</div>
				<div class="cash-dashboard-kpi-item">
					<div class="cash-dashboard-kpi-value is-red">${this.formatInteger(metric.outflow)}</div>
					<div class="cash-dashboard-kpi-label">Расход ${label}</div>
				</div>
				<div class="cash-dashboard-kpi-item">
					<div class="cash-dashboard-kpi-value is-green">${this.formatInteger(metric.end)}</div>
					<div class="cash-dashboard-kpi-label">Конец ${label}</div>
				</div>
			</div>
		`;
	}

	getBalanceMarkup(value, label) {
		return `
			<div class="cash-dashboard-balance-value">${this.formatBalance(value)}</div>
			<div class="cash-dashboard-balance-label">${frappe.utils.escape_html(label)}</div>
		`;
	}

	getTableMarkup(rows, metric, label) {
		return `
			<table class="cash-dashboard-table">
				<thead>
					<tr>
						<th class="is-category">(2)</th>
						<th class="is-number">Прих.${frappe.utils.escape_html(label)}</th>
						<th class="is-number">Расход ${frappe.utils.escape_html(label)}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr class="${row.group ? "is-group" : "is-child"}">
									<td class="is-category ${row.level ? "is-level-1" : ""}">
										${row.group ? '<span class="cash-dashboard-tree-toggle">⊞</span>' : ""}
										<span>${frappe.utils.escape_html(row.label)}</span>
									</td>
									<td class="is-number">${row.inflow ? this.formatInteger(row.inflow) : ""}</td>
									<td class="is-number">${row.outflow ? this.formatInteger(row.outflow) : "0"}</td>
								</tr>
							`
						)
						.join("")}
					<tr class="is-total">
						<td class="is-category">Total</td>
						<td class="is-number">${this.formatInteger(metric.inflow)}</td>
						<td class="is-number">${this.formatInteger(metric.outflow)}</td>
					</tr>
				</tbody>
			</table>
		`;
	}

	getMetrics() {
		const monthIndex = (this.context.months || []).findIndex((month) => month.key === this.state.month);
		const monthFactor = 0.72 + (Math.max(monthIndex, 0) * 0.04);
		const cashBase = this.context.base_kpi?.cash || {};
		const bankBase = this.context.base_kpi?.bank || {};

		const cash = {
			start: Math.round((cashBase.start || 0) * (0.94 + monthFactor * 0.08)),
			target_inflow: Math.round((cashBase.inflow || 0) * monthFactor),
			target_outflow: Math.round((cashBase.outflow || 0) * (0.71 + Math.max(monthIndex, 0) * 0.039)),
		};
		const cashRows = this.getRowsForMonth(this.context.cash_rows || [], cash.target_inflow, "cash");
		cash.inflow = this.sumField(cashRows, "inflow");
		cash.outflow = this.sumField(cashRows, "outflow");
		cash.end = cash.start + cash.inflow - cash.outflow;

		const bank = {
			start: Math.round((bankBase.start || 0) * (0.82 + monthFactor * 0.05)),
			target_inflow: Math.round((bankBase.inflow || 0) * monthFactor),
			target_outflow: Math.round((bankBase.outflow || 0) * (0.74 + Math.max(monthIndex, 0) * 0.033)),
		};
		const bankRows = this.getRowsForMonth(this.context.bank_rows || [], bank.target_inflow, "bank");
		bank.inflow = this.sumField(bankRows, "inflow");
		bank.outflow = this.sumField(bankRows, "outflow");
		bank.end = bank.start + bank.inflow - bank.outflow;

		return { cash, bank };
	}

	getRowsForMonth(rows, salesInflowTarget, key) {
		const monthIndex = (this.context.months || []).findIndex((month) => month.key === this.state.month);
		const factor = 0.74 + (Math.max(monthIndex, 0) * 0.037);

		return rows.map((row, index) => {
			const variance = 1 + ((index % 3) * 0.016);
			let inflow = Math.round((row.inflow || 0) * factor * variance);
			let outflow = Math.round((row.outflow || 0) * factor * (0.99 + ((monthIndex + index) % 2) * 0.02));

			if (key === "cash" && row.label === "Продажа") {
				inflow = salesInflowTarget;
			}

			if (key === "bank" && row.label === "Продажа") {
				inflow = salesInflowTarget;
			}

			return {
				...row,
				inflow,
				outflow,
			};
		});
	}

	sumField(rows, fieldname) {
		return (rows || []).reduce((total, row) => total + (row[fieldname] || 0), 0);
	}

	formatInteger(value) {
		const sign = value < 0 ? "-" : "";
		const numeric = Math.abs(Math.round(value));
		return `${sign}${String(numeric).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}`;
	}

	formatBalance(value) {
		if (!value) {
			return "(Blank)";
		}

		const millions = Math.round(value / 1000000);
		return `${millions}M`;
	}
};
