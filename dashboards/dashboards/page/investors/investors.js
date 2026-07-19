frappe.pages["investors"].on_page_load = function (wrapper) {
	new dashboards.ui.InvestorsPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.InvestorsPage = class InvestorsPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Инвесторы"),
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
		this.investorPalette = ["is-inv-1", "is-inv-2", "is-inv-3"];
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
		this.wrapper.find(".layout-main-section-wrapper").addClass("investors-layout");
		this.wrapper.find(".page-head").addClass("investors-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="inv-screen">
				<section class="inv-main">
					<div class="inv-filters">
						<div class="inv-filter-label">${__("ФИЛЬТР ГОДА")}</div>
						<div class="inv-year-select">
							<button class="inv-select" type="button" data-year-toggle aria-expanded="false">
								<span data-region="selected-year"></span>
								<span class="inv-chevron" aria-hidden="true"></span>
							</button>
							<div class="inv-year-menu" data-region="year-menu"></div>
						</div>
						<div class="inv-filter-label">${__("ФИЛЬТР МЕСЯЦА")}</div>
						<div class="inv-month-grid" data-region="month-grid"></div>
					</div>

					<div class="inv-kpi-grid">
						<section class="inv-card inv-kpi-card inv-kpi-card--profit">
							<div class="inv-card-title">
								<h2>${__("Чистая прибыль")}</h2>
							</div>
							<div class="inv-kpi-row">
								<strong data-region="net-profit"></strong>
							</div>
							<div class="inv-kpi-sub" data-region="net-profit-period"></div>
						</section>
						<section class="inv-card inv-kpi-card inv-kpi-card--paid">
							<div class="inv-card-title">
								<h2>${__("Выплачено инвесторам")}</h2>
							</div>
							<div class="inv-kpi-row">
								<strong data-region="received-total"></strong>
							</div>
							<div class="inv-kpi-sub" data-region="received-period"></div>
						</section>
						<section class="inv-card inv-kpi-card inv-kpi-card--rest">
							<div class="inv-card-title">
								<h2>${__("Остаток к выплате")}</h2>
							</div>
							<div class="inv-kpi-row">
								<strong data-region="remaining-total"></strong>
							</div>
							<div class="inv-kpi-sub" data-region="remaining-period"></div>
						</section>
					</div>

					<div class="inv-content-grid">
						<section class="inv-card inv-table-card">
							<div class="inv-card-head">
								<div class="inv-card-title">
									<span class="inv-title-icon inv-title-icon--blue" aria-hidden="true">☷</span>
									<h2>${__("Распределение прибыли")}</h2>
								</div>
								<div class="inv-period-chip" data-region="period-label"></div>
							</div>
							<div class="inv-table-wrap" data-region="investors-table"></div>
						</section>
					</div>
					<div class="inv-updated" data-region="updated-at"></div>
				</section>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "investors",
		});

		this.$selectedYear = this.page.main.find('[data-region="selected-year"]');
		this.$yearMenu = this.page.main.find('[data-region="year-menu"]');
		this.$monthGrid = this.page.main.find('[data-region="month-grid"]');
		this.$netProfit = this.page.main.find('[data-region="net-profit"]');
		this.$netProfitPeriod = this.page.main.find('[data-region="net-profit-period"]');
		this.$receivedTotal = this.page.main.find('[data-region="received-total"]');
		this.$receivedPeriod = this.page.main.find('[data-region="received-period"]');
		this.$remainingTotal = this.page.main.find('[data-region="remaining-total"]');
		this.$remainingPeriod = this.page.main.find('[data-region="remaining-period"]');
		this.$periodLabel = this.page.main.find('[data-region="period-label"]');
		this.$investorsTable = this.page.main.find('[data-region="investors-table"]');
		this.$updatedAt = this.page.main.find('[data-region="updated-at"]');
	}

	bind_events() {
		this.page.main.off(".investors-dashboard");

		this.page.main.on("click.investors-dashboard", "[data-year-toggle]", (event) => {
			event.stopPropagation();
			const $select = $(event.currentTarget).closest(".inv-year-select");
			const isOpen = $select.hasClass("is-open");
			$select.toggleClass("is-open", !isOpen);
			$(event.currentTarget).attr("aria-expanded", isOpen ? "false" : "true");
		});

		this.page.main.on("click.investors-dashboard", "[data-year]", (event) => {
			const year = String($(event.currentTarget).data("year"));
			this.page.main.find(".inv-year-select").removeClass("is-open");
			this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
			this.load_data({ year, month: this.state.month });
		});

		this.page.main.on("click.investors-dashboard", "[data-month]", (event) => {
			const month = String($(event.currentTarget).attr("data-month") || "");
			// Повторный клик по активному месяцу снимает выбор — годовой режим.
			const nextMonth = month === this.state.month ? "" : month;
			this.load_data({ year: this.state.year, month: nextMonth });
		});

		$(document).off("click.investors-dashboard-year").on("click.investors-dashboard-year", (event) => {
			if ($(event.target).closest(".inv-year-select").length) {
				return;
			}

			this.page.main.find(".inv-year-select").removeClass("is-open");
			this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
		});
	}

	load_data(filters = {}) {
		this.show_loading();
		const year = "year" in filters ? filters.year : this.state.year;
		// Пустой месяц в явном запросе — годовой режим ("all"); при первой загрузке
		// месяц не передается, и бэкенд выбирает текущий месяц по умолчанию.
		const hasExplicitMonth = "month" in filters;
		const month = hasExplicitMonth ? filters.month : this.state.month;
		return frappe
			.call({
				method: "dashboards.dashboards.page.investors.investors.get_dashboard_data",
				args: {
					year: year || undefined,
					month: hasExplicitMonth && !month ? "all" : month || undefined,
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
				frappe.msgprint(__("Не удалось загрузить данные дашборда инвесторов."));
				this.render_empty();
			});
	}

	show_loading() {
		this.$selectedYear.text(this.state.year || "...");
		this.$yearMenu.empty();
		this.$monthGrid.html(this.months.map((month) => this.render_month_button(month)).join(""));
		const loadingMarkup = `<div class="inv-loading">${__("Загрузка...")}</div>`;
		this.$netProfit.text("...");
		this.$receivedTotal.text("...");
		this.$remainingTotal.text("...");
		this.$investorsTable.html(loadingMarkup);
	}

	render_empty() {
		this.$investorsTable.html(`<div class="inv-loading">${__("Нет данных")}</div>`);
	}

	render() {
		const summary = this.data?.summary || {};
		const periodLabel = this.data?.period_label || "";
		this.$selectedYear.text(this.state.year);
		this.$yearMenu.html(this.years.map((year) => this.render_year_option(year)).join(""));
		this.$monthGrid.html(this.months.map((month) => this.render_month_button(month)).join(""));

		this.$netProfit.text(summary.net_profit_display || "0 UZS");
		this.$netProfit.toggleClass("is-negative", Number(summary.net_profit || 0) < 0);
		this.$receivedTotal.text(summary.received_total_display || "0 UZS");
		this.$remainingTotal.text(summary.remaining_total_display || "0 UZS");
		this.$remainingTotal.toggleClass("is-negative", Number(summary.remaining_total || 0) < 0);
		this.$netProfitPeriod.text(periodLabel);
		this.$receivedPeriod.text(periodLabel);
		this.$remainingPeriod.text(periodLabel);
		this.$periodLabel.text(periodLabel);
		this.$updatedAt.text(`${__("Последнее обновление")}: ${this.data?.updated_at || "—"}`);

		this.render_investors_table();
	}

	render_year_option(year) {
		return `<button class="inv-year-option ${year === this.state.year ? "is-active" : ""}" type="button" data-year="${year}">${frappe.utils.escape_html(year)}</button>`;
	}

	render_month_button(month) {
		return `<button class="inv-month ${month.key === this.state.month ? "is-active" : ""}" type="button" data-month="${month.key}">${frappe.utils.escape_html(month.label)}</button>`;
	}

	render_status_chip(row) {
		const remaining = Number(row.remaining || 0);
		if (row.is_overdrawn && Math.abs(remaining) >= 1) {
			return `<span class="inv-chip inv-chip--red">${__("переплата")}</span>`;
		}
		if (remaining >= 1) {
			return `<span class="inv-chip inv-chip--gold">${__("к выплате")}</span>`;
		}
		return `<span class="inv-chip inv-chip--green">${__("выплачено")}</span>`;
	}

	render_investors_table() {
		const rows = this.data?.investors || [];
		const totals = this.data?.totals || {};
		if (!rows.length) {
			this.$investorsTable.html(`<div class="inv-loading">${__("Нет данных")}</div>`);
			return;
		}

		this.$investorsTable.html(`
			<table class="inv-table">
				<thead>
					<tr>
						<th class="is-text">${__("Инвестор")}</th>
						<th class="is-number">${__("Доля")}</th>
						<th class="is-number">${__("Должен получить")}</th>
						<th class="is-number is-progress">${__("Получено")}</th>
						<th class="is-number">${__("Остаток")}</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map((row, index) => {
							const paletteClass = this.investorPalette[index % this.investorPalette.length];
							const progress =
								row.received_pct === null || row.received_pct === undefined
									? ""
									: `
										<div class="inv-progress">
											<div class="inv-progress-fill ${paletteClass}" style="width: ${Math.max(0, Math.min(100, Number(row.received_pct)))}%"></div>
										</div>
										<span class="inv-progress-value">${frappe.utils.escape_html(`${this.format_decimal(row.received_pct, 1)}%`)}</span>
									`;
							return `
								<tr>
									<td class="is-text">
										<span class="inv-dot ${paletteClass}" aria-hidden="true"></span>
										${frappe.utils.escape_html(row.label || "")}
									</td>
									<td class="is-number"><span class="inv-share-badge ${paletteClass}">${frappe.utils.escape_html(row.share_pct_display || "")}</span></td>
									<td class="is-number">${frappe.utils.escape_html(row.due_display || this.format_money(row.due))}</td>
									<td class="is-number is-progress">
										<div class="inv-received">${frappe.utils.escape_html(row.received_display || this.format_money(row.received))}</div>
										${progress}
									</td>
									<td class="is-number ${row.is_overdrawn ? "is-negative" : ""}">
										${frappe.utils.escape_html(row.remaining_display || this.format_money(row.remaining))}
										${this.render_status_chip(row)}
									</td>
								</tr>
							`;
						})
						.join("")}
				</tbody>
				<tfoot>
					<tr>
						<td class="is-text">${__("Итого")}</td>
						<td class="is-number">${frappe.utils.escape_html(totals.share_pct_display || "100%")}</td>
						<td class="is-number">${frappe.utils.escape_html(totals.due_display || this.format_money(totals.due))}</td>
						<td class="is-number is-progress">${frappe.utils.escape_html(totals.received_display || this.format_money(totals.received))}</td>
						<td class="is-number ${Number(totals.remaining || 0) < 0 ? "is-negative" : ""}">${frappe.utils.escape_html(totals.remaining_display || this.format_money(totals.remaining))}</td>
					</tr>
				</tfoot>
			</table>
		`);
	}

	format_decimal(value, maximumFractionDigits = 1) {
		return new Intl.NumberFormat("ru-RU", {
			maximumFractionDigits,
			minimumFractionDigits: 0,
		}).format(value || 0);
	}

	format_money(value) {
		return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(value || 0)} UZS`;
	}
};
