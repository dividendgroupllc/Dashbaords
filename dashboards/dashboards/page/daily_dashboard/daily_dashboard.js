frappe.pages["daily-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.DailyDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.DailyDashboardPage = class DailyDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Daily Dashboard"),
			single_column: true,
		});

		this.state = {
			year: null,
			month: null,
			client: null,
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("daily-dashboard-layout");
		this.wrapper.find(".page-head").addClass("daily-dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="daily-dashboard-screen">
				<div class="daily-dashboard-shell">
					<div class="daily-dashboard-topbar">
						<div class="daily-dashboard-brand">
							<div class="daily-dashboard-logo">PM</div>
							<div class="daily-dashboard-title-block">
								<div class="daily-dashboard-title-primary" data-region="title-primary"></div>
								<div class="daily-dashboard-title-secondary" data-region="title-secondary"></div>
							</div>
						</div>
						<div class="daily-dashboard-years" data-region="years"></div>
						<div class="daily-dashboard-info">i</div>
					</div>
					<div class="daily-dashboard-months" data-region="months"></div>
					<div class="daily-dashboard-clients" data-region="clients"></div>
					<div class="daily-dashboard-content">
						<div class="daily-dashboard-calendar-panel">
							<div class="daily-dashboard-calendar-title" data-region="calendar-title"></div>
							<div class="daily-dashboard-calendar-weekdays" data-region="weekdays"></div>
							<div class="daily-dashboard-calendar-grid" data-region="calendar"></div>
						</div>
						<div class="daily-dashboard-table-panel">
							<div class="daily-dashboard-table-wrap" data-region="table"></div>
						</div>
					</div>
				</div>
			</div>
		`);

		this.$titlePrimary = this.page.main.find('[data-region="title-primary"]');
		this.$titleSecondary = this.page.main.find('[data-region="title-secondary"]');
		this.$years = this.page.main.find('[data-region="years"]');
		this.$months = this.page.main.find('[data-region="months"]');
		this.$clients = this.page.main.find('[data-region="clients"]');
		this.$calendarTitle = this.page.main.find('[data-region="calendar-title"]');
		this.$weekdays = this.page.main.find('[data-region="weekdays"]');
		this.$calendar = this.page.main.find('[data-region="calendar"]');
		this.$table = this.page.main.find('[data-region="table"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.daily_dashboard.daily_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.state = { ...(this.context.default_filters || {}) };
				this.render();
			},
		});
	}

	render() {
		this.$titlePrimary.text(this.context.title_primary || "");
		this.$titleSecondary.text(this.context.title_secondary || "");
		this.render_years();
		this.render_months();
		this.render_clients();
		this.render_calendar();
		this.render_table();
	}

	render_years() {
		const years = this.context.years || [];
		this.$years.html(
			years
				.map(
					(year) => `
						<button class="daily-dashboard-chip daily-dashboard-chip--year ${year === this.state.year ? "is-active" : ""}" data-year="${year}">
							${frappe.utils.escape_html(year)}
						</button>
					`
				)
				.join("") +
				`<div class="daily-dashboard-year-spinner"><span></span><span></span></div>`
		);

		this.$years.find("[data-year]").on("click", (e) => {
			this.state.year = String($(e.currentTarget).data("year"));
			this.render();
		});
	}

	render_months() {
		const months = this.context.months || [];
		this.$months.html(
			months
				.map(
					(month) => `
						<button class="daily-dashboard-chip daily-dashboard-chip--month ${month.key === this.state.month ? "is-active" : ""}" data-month="${month.key}">
							${frappe.utils.escape_html(month.label)}
						</button>
					`
				)
				.join("")
		);

		this.$months.find("[data-month]").on("click", (e) => {
			this.state.month = String($(e.currentTarget).data("month"));
			this.render();
		});
	}

	render_clients() {
		const clients = this.context.clients || [];
		this.$clients.html(
			clients
				.map(
					(client) => `
						<button class="daily-dashboard-chip daily-dashboard-chip--client ${client === this.state.client ? "is-active" : ""}" data-client="${frappe.utils.escape_html(
							client
						)}">
							${frappe.utils.escape_html(client)}
						</button>
					`
				)
				.join("")
		);

		this.$clients.find("[data-client]").on("click", (e) => {
			this.state.client = String($(e.currentTarget).data("client"));
			this.render_calendar();
			this.render_table();
			this.render_clients();
		});
	}

	render_calendar() {
		const date = this.getActiveDate();
		const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
		const values = this.getCalendarValues();
		const firstDayOffset = (date.getDay() + 6) % 7;
		const lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
		const cells = [];

		for (let index = 0; index < firstDayOffset; index += 1) {
			cells.push('<div class="daily-dashboard-calendar-cell is-empty"></div>');
		}

		for (let day = 1; day <= lastDay; day += 1) {
			const value = values[day] || null;
			cells.push(`
				<div class="daily-dashboard-calendar-cell ${value ? this.getHeatClass(value, values) : "is-blank"} ${day === date.getDate() ? "is-current-day" : ""}">
					<div class="daily-dashboard-calendar-day">${day}</div>
					<div class="daily-dashboard-calendar-value">${value ? this.formatInteger(value) : ""}</div>
				</div>
			`);
		}

		this.$calendarTitle.text(`${this.getMonthLabel(this.state.month)} ${this.state.year}`);
		this.$weekdays.html(
			weekdays
				.map((weekday) => `<div class="daily-dashboard-weekday">${frappe.utils.escape_html(weekday)}</div>`)
				.join("")
		);
		this.$calendar.html(cells.join(""));
	}

	render_table() {
		const rows = this.getProductRows();
		const total = this.buildTotalRow(rows);
		const headers = ["Предметы", "КГ", "Сумма.прод", "Сумма себест", "Маржа", "РСП сумма", "рен", "ЧП", "ЧП рен"];

		this.$table.html(`
			<table class="daily-dashboard-table">
				<thead>
					<tr>${headers.map((header) => `<th>${frappe.utils.escape_html(header)}</th>`).join("")}</tr>
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
									<td class="is-number">${this.formatPercent(row.profitability)}</td>
									<td class="is-number">${this.formatInteger(row.np)}</td>
									<td class="is-number">${this.formatSignedPercent(row.np_profitability)}</td>
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
						<td class="is-number">${this.formatPercent(total.profitability)}</td>
						<td class="is-number">${this.formatInteger(total.np)}</td>
						<td class="is-number">${this.formatSignedPercent(total.np_profitability)}</td>
					</tr>
				</tbody>
			</table>
		`);
	}

	getActiveDate() {
		const monthIndex = (this.context.months || []).findIndex((month) => month.key === this.state.month);
		return new Date(Number(this.state.year), monthIndex >= 0 ? monthIndex : 11, 1);
	}

	getMonthLabel(monthKey) {
		const month = (this.context.months || []).find((item) => item.key === monthKey);
		return month ? month.label : "";
	}

	getCalendarValues() {
		const base = this.context.calendar_values || {};
		const yearFactorMap = {
			"2021": 0.76,
			"2023": 0.89,
			"2024": 1,
			"2025": 1.08,
		};
		const monthIndex = (this.context.months || []).findIndex((month) => month.key === this.state.month);
		const monthFactor = 0.68 + (Math.max(monthIndex, 0) * 0.035);
		const clientIndex = Math.max((this.context.clients || []).indexOf(this.state.client), 0);
		const clientFactor = 0.93 + ((clientIndex % 7) * 0.023);
		const factor = (yearFactorMap[this.state.year] || 1) * monthFactor * clientFactor;
		const values = {};

		Object.keys(base).forEach((day) => {
			values[day] = Math.max(0, Math.round(base[day] * factor));
		});

		return values;
	}

	getProductRows() {
		const baseRows = this.context.product_rows || [];
		const yearFactorMap = {
			"2021": 0.82,
			"2023": 0.91,
			"2024": 1,
			"2025": 1.06,
		};
		const monthIndex = (this.context.months || []).findIndex((month) => month.key === this.state.month);
		const clientIndex = Math.max((this.context.clients || []).indexOf(this.state.client), 0);
		const monthFactor = 0.72 + (Math.max(monthIndex, 0) * 0.03);
		const clientFactor = 0.9 + ((clientIndex % 9) * 0.02);
		const factor = (yearFactorMap[this.state.year] || 1) * monthFactor * clientFactor;

		return baseRows.map((row, rowIndex) => {
			const variance = 1 + (((clientIndex + rowIndex) % 4) * 0.01);
			const sales = Math.round(row.sales * factor * variance);
			const cost = Math.round(row.cost * factor * (0.99 + (rowIndex % 3) * 0.01));
			const margin = sales - cost;
			const rsp = Math.round(row.rsp * factor * (0.98 + ((monthIndex + rowIndex) % 3) * 0.02));
			const np = margin - rsp;
			return {
				item: row.item,
				kg: Math.round(row.kg * factor * variance),
				sales: sales,
				cost: cost,
				margin: margin,
				rsp: rsp,
				profitability: sales ? (margin / sales) * 100 : 0,
				np: np,
				np_profitability: sales ? (np / sales) * 100 : 0,
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
				accumulator.np += row.np;
				return accumulator;
			},
			{ kg: 0, sales: 0, cost: 0, margin: 0, rsp: 0, np: 0 }
		);

		total.profitability = total.sales ? (total.margin / total.sales) * 100 : 0;
		total.np_profitability = total.sales ? (total.np / total.sales) * 100 : 0;
		return total;
	}

	getHeatClass(value, values) {
		const numericValues = Object.values(values).filter(Boolean);
		const max = Math.max(...numericValues, 1);
		const ratio = value / max;

		if (ratio >= 0.85) return "heat-5";
		if (ratio >= 0.65) return "heat-4";
		if (ratio >= 0.45) return "heat-3";
		if (ratio >= 0.2) return "heat-2";
		return "heat-1";
	}

	formatInteger(value) {
		const sign = value < 0 ? "-" : "";
		const numeric = Math.abs(Math.round(value));
		return `${sign}${String(numeric).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}`;
	}

	formatPercent(value) {
		return `${this.formatDecimal(value)}%`;
	}

	formatSignedPercent(value) {
		return `${value < 0 ? "-" : ""}${this.formatDecimal(Math.abs(value))}%`;
	}

	formatDecimal(value) {
		return Number(value || 0).toFixed(1).replace(".", ",");
	}
};
