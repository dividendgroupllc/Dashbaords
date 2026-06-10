frappe.pages["manufacture-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.ManufactureDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.ManufactureDashboardPage = class ManufactureDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Производственный дашборд"),
			single_column: true,
		});

		this.months = [
			{ key: "Jan", label: "Янв", full: "Январь" },
			{ key: "Feb", label: "Фев", full: "Февраль" },
			{ key: "Mar", label: "Мар", full: "Март" },
			{ key: "Apr", label: "Апр", full: "Апрель" },
			{ key: "May", label: "Май", full: "Май" },
			{ key: "Jun", label: "Июн", full: "Июнь" },
			{ key: "Jul", label: "Июл", full: "Июль" },
			{ key: "Aug", label: "Авг", full: "Август" },
			{ key: "Sep", label: "Сен", full: "Сентябрь" },
			{ key: "Oct", label: "Окт", full: "Октябрь" },
			{ key: "Nov", label: "Ноя", full: "Ноябрь" },
			{ key: "Dec", label: "Дек", full: "Декабрь" },
		];
		this.years = [];
		this.state = {
			year: "",
			month: "",
		};
		this.data = null;

		this.make_layout();
		this.bind_events();
		this.load_data();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("manufacture-dashboard-layout");
		this.wrapper.find(".page-head").addClass("manufacture-dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="mfd-screen">
				<section class="mfd-main">
					<div class="mfd-filters">
						<div class="mfd-filter-label">${__("ФИЛЬТР ГОДА")}</div>
						<div class="mfd-year-select">
							<button class="mfd-select" type="button" data-year-toggle aria-expanded="false">
								<span data-region="selected-year"></span>
								<span class="mfd-chevron" aria-hidden="true"></span>
							</button>
							<div class="mfd-year-menu" data-region="year-menu"></div>
						</div>
						<div class="mfd-filter-label">${__("ФИЛЬТР МЕСЯЦА")}</div>
						<div class="mfd-month-grid" data-region="month-grid"></div>
					</div>

					<div class="mfd-kpi-grid">
						<section class="mfd-card mfd-kpi-card mfd-kpi-card--production">
							<div class="mfd-card-title">
								<span class="mfd-title-icon mfd-title-icon--blue" aria-hidden="true">▧</span>
								<h2>${__("Производство за текущий месяц")}</h2>
							</div>
							<div class="mfd-kpi-row">
								<strong data-region="month-production"></strong>
							</div>
						</section>
						<section class="mfd-card mfd-kpi-card mfd-kpi-card--extra-expense">
							<div class="mfd-card-title">
								<span class="mfd-title-icon mfd-title-icon--green" aria-hidden="true">⌑</span>
								<h2>${__("Доп. расход")}</h2>
							</div>
							<div class="mfd-kpi-row">
								<strong data-region="dop-rasxod-total"></strong>
							</div>
						</section>
						<section class="mfd-card mfd-kpi-card mfd-kpi-card--cost">
							<div class="mfd-card-title">
								<span class="mfd-title-icon mfd-title-icon--violet" aria-hidden="true">⌁</span>
								<h2>${__("Сумма себестоимости")}</h2>
							</div>
							<div class="mfd-kpi-row">
								<strong data-region="average-cost"></strong>
							</div>
						</section>
					</div>

					<div class="mfd-chart-grid">
						<section class="mfd-card mfd-volume-card">
							<div class="mfd-card-head">
								<div class="mfd-card-title">
									<span class="mfd-title-icon mfd-title-icon--blue" aria-hidden="true">⌞</span>
									<h2>${__("Годовой объем производства")}</h2>
								</div>
								<div class="mfd-legend">
									<span><i class="is-blue"></i>${__("Тонны")}</span>
								</div>
							</div>
							<div class="mfd-combo-chart" data-region="combo-chart"></div>
						</section>

						<section class="mfd-card mfd-production-table-card">
							<div class="mfd-card-title">
								<span class="mfd-title-icon mfd-title-icon--green" aria-hidden="true">☷</span>
								<h2>${__("Произведенные товары за месяц")}</h2>
							</div>
							<div class="mfd-production-table-wrap" data-region="production-table"></div>
						</section>
					</div>
					<div class="mfd-updated" data-region="updated-at"></div>
				</section>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "manufacture-dashboard",
		});

		this.$selectedYear = this.page.main.find('[data-region="selected-year"]');
		this.$yearMenu = this.page.main.find('[data-region="year-menu"]');
		this.$monthGrid = this.page.main.find('[data-region="month-grid"]');
		this.$monthProduction = this.page.main.find('[data-region="month-production"]');
		this.$dopRasxodTotal = this.page.main.find('[data-region="dop-rasxod-total"]');
		this.$averageCost = this.page.main.find('[data-region="average-cost"]');
		this.$comboChart = this.page.main.find('[data-region="combo-chart"]');
		this.$productionTable = this.page.main.find('[data-region="production-table"]');
		this.$updatedAt = this.page.main.find('[data-region="updated-at"]');
	}

	bind_events() {
		this.page.main.off(".manufacture-dashboard");

		this.page.main.on("click.manufacture-dashboard", "[data-year-toggle]", (event) => {
			event.stopPropagation();
			const $select = $(event.currentTarget).closest(".mfd-year-select");
			const isOpen = $select.hasClass("is-open");
			$select.toggleClass("is-open", !isOpen);
			$(event.currentTarget).attr("aria-expanded", isOpen ? "false" : "true");
		});

		this.page.main.on("click.manufacture-dashboard", "[data-year]", (event) => {
			const year = String($(event.currentTarget).data("year"));
			this.page.main.find(".mfd-year-select").removeClass("is-open");
			this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
			this.load_data({ year, month: this.state.month });
		});

		this.page.main.on("click.manufacture-dashboard", "[data-month]", (event) => {
			const month = String($(event.currentTarget).data("month"));
			this.load_data({ year: this.state.year, month });
		});

		$(document).off("click.manufacture-dashboard-year").on("click.manufacture-dashboard-year", (event) => {
			if ($(event.target).closest(".mfd-year-select").length) {
				return;
			}

			this.page.main.find(".mfd-year-select").removeClass("is-open");
			this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
		});
	}

	load_data(filters = {}) {
		this.show_loading();
		return frappe
			.call({
				method: "dashboards.dashboards.page.manufacture_dashboard.manufacture_dashboard.get_dashboard_data",
				args: {
					year: filters.year || this.state.year || undefined,
					month: filters.month || this.state.month || undefined,
				},
			})
			.then((response) => {
				this.data = response.message || {};
				const backendFilters = this.data.filters || {};
				this.years = backendFilters.years || [];
				this.state.year = backendFilters.selected_year || "";
				this.state.month = backendFilters.selected_month || "";
				this.render();
			})
			.catch(() => {
				frappe.msgprint(__("Не удалось загрузить данные производственного дашборда."));
				this.render_empty();
			});
	}

	show_loading() {
		this.$selectedYear.text(this.state.year || "...");
		this.$yearMenu.empty();
		this.$monthGrid.html(this.months.map((month) => this.render_month_button(month)).join(""));
		const loadingMarkup = `<div class="mfd-loading">${__("Загрузка...")}</div>`;
		this.$monthProduction.text("...");
		this.$dopRasxodTotal.text("...");
		this.$averageCost.text("...");
		this.$comboChart.html(loadingMarkup);
		this.$productionTable.html(loadingMarkup);
	}

	render_empty() {
		this.$comboChart.html(`<div class="mfd-loading">${__("Нет данных")}</div>`);
		this.$productionTable.html(`<div class="mfd-loading">${__("Нет данных")}</div>`);
	}

	render() {
		const summary = this.data?.summary || {};
		this.$selectedYear.text(this.state.year);
		this.$yearMenu.html(this.years.map((year) => this.render_year_option(year)).join(""));
		this.$monthGrid.html(this.months.map((month) => this.render_month_button(month)).join(""));
		this.$monthProduction.text(summary.monthProductionDisplay || `0 ${__("T")}`);
		this.$dopRasxodTotal.text(summary.dopRasxodTotalDisplay || "0 UZS");
		this.$averageCost.text(summary.summaSebTotalDisplay || "0 UZS");
		this.$updatedAt.text(`${__("Последнее обновление")}: ${this.data?.updated_at || "—"}`);
		this.render_combo_chart();
		this.render_production_table();
	}

	render_year_option(year) {
		return `<button class="mfd-year-option ${year === this.state.year ? "is-active" : ""}" type="button" data-year="${year}">${frappe.utils.escape_html(year)}</button>`;
	}

	render_month_button(month) {
		return `<button class="mfd-month ${month.key === this.state.month ? "is-active" : ""}" type="button" data-month="${month.key}">${frappe.utils.escape_html(month.label)}</button>`;
	}

	render_combo_chart() {
		const rows = this.data?.monthly || [];
		if (!rows.length) {
			this.$comboChart.html(`<div class="mfd-loading">${__("Нет данных")}</div>`);
			return;
		}
		const maxTon = Math.max(1, ...rows.map((row) => Number(row.ton || 0)));

		this.$comboChart.html(`
			<div class="mfd-y-axis mfd-y-axis--left">
				${this.build_axis_labels(maxTon, 8, (value) => this.format_number(value)).map((label) => `<span>${label}</span>`).join("")}
			</div>
			<div class="mfd-bars">
				${rows
					.map((row) => {
						const month = this.months.find((item) => item.key === row.month);
						return `
							<div class="mfd-bar-item">
								<span class="mfd-bar-value">${frappe.utils.escape_html(row.ton_display || `${this.format_number(row.ton)} T`)}</span>
								<div class="mfd-bar" style="height: ${Math.max(2, Math.round((Number(row.ton || 0) / maxTon) * 92))}%"></div>
								<span class="mfd-bar-label">${frappe.utils.escape_html(month ? month.full : row.month)}</span>
							</div>
						`;
					})
					.join("")}
			</div>
		`);
	}

	render_production_table() {
		const rows = this.data?.production_rows || [];
		if (!rows.length) {
			this.$productionTable.html(`<div class="mfd-loading">${__("Нет данных")}</div>`);
			return;
		}

		const total = rows.reduce(
			(accumulator, row) => {
				accumulator.ton += Number(row.ton_raw ?? row.ton ?? 0);
				accumulator.summaSeb += Number(row.summa_seb_raw ?? row.summa_seb ?? 0);
				accumulator.dopRasxod += Number(row.dop_rasxod_raw ?? row.dop_rasxod ?? 0);
				return accumulator;
			},
			{ ton: 0, summaSeb: 0, dopRasxod: 0 }
		);

		this.$productionTable.html(`
			<table class="mfd-production-table">
				<thead>
					<tr>
						<th class="is-text">${__("Наименование товара")}</th>
						<th class="is-number">${__("Тонны")}</th>
						<th class="is-number">${__("Сумма себестоимости")}</th>
						<th class="is-number">${__("Доп. расход")}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr>
									<td class="is-text">${frappe.utils.escape_html(row.label || "")}</td>
									<td class="is-number">${frappe.utils.escape_html(row.ton_display || `${this.format_decimal(row.ton, 2)} T`)}</td>
									<td class="is-number">${frappe.utils.escape_html(row.summa_seb_display || this.format_number(row.summa_seb))}</td>
									<td class="is-number">${frappe.utils.escape_html(row.dop_rasxod_display || this.format_number(row.dop_rasxod))}</td>
								</tr>
							`
						)
						.join("")}
				</tbody>
				<tfoot>
					<tr>
						<td class="is-text">${__("Итого")}</td>
						<td class="is-number">${frappe.utils.escape_html(`${this.format_decimal(total.ton, 2)} T`)}</td>
						<td class="is-number">${frappe.utils.escape_html(`${this.format_number(total.summaSeb)} UZS`)}</td>
						<td class="is-number">${frappe.utils.escape_html(`${this.format_number(total.dopRasxod)} UZS`)}</td>
					</tr>
				</tfoot>
			</table>
		`);
	}

	build_axis_labels(maxValue, count, formatter) {
		const max = Math.max(Number(maxValue || 0), 1);
		return Array.from({ length: count }, (_, index) => {
			const value = max - (max / (count - 1)) * index;
			return formatter(value);
		});
	}

	format_compact_money(value) {
		const amount = Number(value || 0);
		const absolute = Math.abs(amount);
		if (absolute >= 1_000_000_000) {
			return `${this.format_decimal(amount / 1_000_000_000, 1)}B`;
		}
		if (absolute >= 1_000_000) {
			return `${this.format_decimal(amount / 1_000_000, 1)}M`;
		}
		if (absolute >= 1_000) {
			return `${this.format_decimal(amount / 1_000, 1)}K`;
		}
		return this.format_number(amount);
	}

	format_decimal(value, maximumFractionDigits = 1) {
		return new Intl.NumberFormat("en-US", {
			maximumFractionDigits,
			minimumFractionDigits: 0,
		}).format(value || 0);
	}

	format_number(value) {
		return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value || 0);
	}
};
