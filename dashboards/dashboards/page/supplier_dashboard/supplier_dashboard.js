frappe.pages["supplier-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.SupplierDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.SupplierDashboardPage = class SupplierDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Панель поставщиков"),
			single_column: true,
		});
		this.state = {
			year: null,
			month: null,
			supplier: null,
		};
		this.monthLabels = {
			Январь: "Янв",
			Февраль: "Фев",
			Март: "Мар",
			Апрель: "Апр",
			Май: "Май",
			Июнь: "Июн",
			Июль: "Июл",
			Август: "Авг",
			Сентябрь: "Сен",
			Октябрь: "Окт",
			Ноябрь: "Ноя",
			Декабрь: "Дек",
		};

		this.make_layout();
		this.bind_events();
		this.load_context();
	}

	ensure_runtime_styles() {
		if (document.getElementById("supplier-dashboard-runtime-filter-fix")) {
			return;
		}

		const style = document.createElement("style");
		style.id = "supplier-dashboard-runtime-filter-fix";
		style.textContent = `
			.supplier-dashboard-filters {
				display: grid;
				grid-template-columns: 1fr;
				gap: 12px;
				overflow: hidden;
			}
			.supplier-dashboard-period-row {
				display: flex;
				align-items: center;
				gap: 12px;
				min-width: 0;
			}
			.supplier-dashboard-filter-label {
				flex: 0 0 auto;
			}
			.supplier-dashboard-year-select {
				flex: 0 0 110px;
			}
			.supplier-dashboard-month-grid {
				display: grid;
				flex: 1 1 auto;
				grid-template-columns: repeat(auto-fit, minmax(52px, 1fr));
				gap: 8px;
				min-width: 0;
				width: 100%;
			}
			.supplier-dashboard-month {
				min-width: 0;
			}
			@media (max-width: 900px) {
				.supplier-dashboard-period-row {
					align-items: stretch;
					flex-direction: column;
				}
			}
		`;
		document.head.appendChild(style);
	}

	make_layout() {
		this.ensure_runtime_styles();
		this.wrapper.find(".layout-main-section-wrapper").addClass("supplier-dashboard-layout");
		this.wrapper.find(".page-head").addClass("supplier-dashboard-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="supplier-dashboard-screen">
				<div class="supplier-dashboard-shell">
					<header class="supplier-dashboard-header">
						<div class="supplier-dashboard-brand">
							<div class="supplier-dashboard-logo" data-region="logo">S</div>
							<div class="supplier-dashboard-brand-copy">
								<div class="supplier-dashboard-title">4 ИНФОРМАЦИОННАЯ ПАНЕЛЬ</div>
								<div class="supplier-dashboard-subtitle" data-region="company"></div>
							</div>
						</div>
						<div class="supplier-dashboard-info">i</div>
					</header>
					<div class="supplier-dashboard-filters">
						<div class="supplier-dashboard-period-row supplier-dashboard-period-row--year">
							<div class="supplier-dashboard-filter-label">ФИЛЬТР ГОДА</div>
							<div class="supplier-dashboard-year-select">
								<button class="supplier-dashboard-select" type="button" data-year-toggle aria-expanded="false">
									<span data-region="selected-year">...</span>
									<span class="supplier-dashboard-chevron"></span>
								</button>
								<div class="supplier-dashboard-year-menu" data-region="years"></div>
							</div>
						</div>
						<div class="supplier-dashboard-period-row supplier-dashboard-period-row--months">
							<div class="supplier-dashboard-filter-label">ФИЛЬТР МЕСЯЦА</div>
							<div class="supplier-dashboard-month-grid" data-region="months"></div>
						</div>
					</div>
					<div class="supplier-dashboard-body">
						<aside class="supplier-dashboard-kpis" data-region="kpis"></aside>
						<section class="supplier-dashboard-table-panel">
							<div class="supplier-dashboard-table-meta" data-region="period"></div>
							<div class="supplier-dashboard-table-wrap" data-region="table"></div>
						</section>
					</div>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "supplier-dashboard",
		});

		this.$company = this.page.main.find('[data-region="company"]');
		this.$logo = this.page.main.find('[data-region="logo"]');
		this.$period = this.page.main.find('[data-region="period"]');
		this.$selectedYear = this.page.main.find('[data-region="selected-year"]');
		this.$years = this.page.main.find('[data-region="years"]');
		this.$months = this.page.main.find('[data-region="months"]');
		this.$yearSelect = this.page.main.find(".supplier-dashboard-year-select");
		this.$kpis = this.page.main.find('[data-region="kpis"]');
		this.$table = this.page.main.find('[data-region="table"]');
	}

	bind_events() {
		this.page.main.on("click", "[data-year-toggle]", (e) => {
			e.preventDefault();
			e.stopPropagation();
			const isOpen = this.$yearSelect.hasClass("is-open");
			this.$yearSelect.toggleClass("is-open", !isOpen);
			$(e.currentTarget).attr("aria-expanded", String(!isOpen));
		});

		$(document)
			.off("click.supplier-dashboard-year-menu")
			.on("click.supplier-dashboard-year-menu", (e) => {
				if (!$(e.target).closest(".supplier-dashboard-year-select").length) {
					this.$yearSelect.removeClass("is-open");
					this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
				}
			});
	}

	load_context(filters = {}) {
		this.render_loading();

		frappe.call({
			method: "dashboards.dashboards.page.supplier_dashboard.supplier_dashboard.get_dashboard_context",
			args: {
				year: Object.prototype.hasOwnProperty.call(filters, "year") ? filters.year : this.state.year,
				month: Object.prototype.hasOwnProperty.call(filters, "month") ? filters.month : this.state.month,
				supplier: Object.prototype.hasOwnProperty.call(filters, "supplier") ? filters.supplier : this.state.supplier,
			},
			callback: (r) => {
				this.context = r.message || {};
				this.state = { ...(this.context.default_filters || {}) };
				this.render();
			},
		});
	}

	render() {
		const companyName = this.context.company_name || __("Компания");
		this.$company.text(companyName);
		this.$logo.text((companyName || "S").trim().slice(0, 1).toUpperCase());
		const selectedSupplierName = this.context.selected_supplier_name;
		this.$period.text(
			selectedSupplierName ? `Период: ${this.context.period_label || ""} • Поставщик: ${selectedSupplierName}` : `Период: ${this.context.period_label || ""}`
		);
		this.render_filters();
		this.render_kpis();
		this.render_table();
	}

	render_filters() {
		this.$selectedYear.text(this.state.year || "...");
		this.$years.html(
			(this.context.years || [])
				.map(
					(year) => `
						<button class="supplier-dashboard-year-option ${year === this.state.year ? "is-active" : ""}" data-year="${year}">
							${frappe.utils.escape_html(year)}
						</button>
					`
				)
				.join("")
		);

		this.$months.html(
			(this.context.months || [])
				.map(
					(month) => `
						<button class="supplier-dashboard-month ${month === this.state.month ? "is-active" : ""}" data-month="${month}">
							${frappe.utils.escape_html(this.monthLabels[month] || month)}
						</button>
					`
				)
				.join("")
		);

		this.$years.find("[data-year]").on("click", (e) => {
			this.$yearSelect.removeClass("is-open");
			this.page.main.find("[data-year-toggle]").attr("aria-expanded", "false");
			this.load_context({
				year: String($(e.currentTarget).data("year")),
				supplier: null,
			});
		});

		this.$months.find("[data-month]").on("click", (e) => {
			const month = String($(e.currentTarget).data("month"));
			this.load_context({
				month: month === this.state.month ? null : month,
				supplier: null,
			});
		});
	}

	render_kpis() {
		const kpis = this.context.kpis || {};
		const cards = [
			{ value: kpis.sum_prepayment, label: "Предоплата", kind: "prepayment" },
			{ value: kpis.sum_debt, label: "Долг", kind: "debt" },
		];

		this.$kpis.html(
			cards
				.map(
					(card) => `
						<div class="supplier-dashboard-kpi-card">
							<div class="supplier-dashboard-kpi-value">${this.formatKpi(card.value, card.kind)}</div>
							<div class="supplier-dashboard-kpi-label">${card.label}</div>
						</div>
					`
				)
				.join("")
		);
	}

	render_table() {
		const rows = this.context.rows || [];
		const totals = this.context.totals || {};
		const columns = this.context.columns || {};

		if (!rows.length) {
			this.$table.html(`<div class="supplier-dashboard-empty">${__("Данные по поставщикам не найдены.")}</div>`);
			return;
		}

		this.$table.html(`
			<table class="supplier-dashboard-table">
				<thead>
					<tr>
						<th class="is-text">Имя поставщика:</th>
						<th>Начало</th>
						<th>Приход</th>
						<th>Оплата наличными</th>
						<th>Оплата банком</th>
						<th>${frappe.utils.escape_html(columns.local_balance_label || "Сум остаток")}</th>
						<th>Рен</th>
					</tr>
				</thead>
				<tbody>
					${rows
						.map(
							(row) => `
								<tr>
									<td class="is-text">
										<button
											type="button"
											class="supplier-dashboard-supplier-link ${row.supplier === this.state.supplier ? "is-active" : ""}"
											data-supplier="${frappe.utils.escape_html(row.supplier || "")}"
										>
											${frappe.utils.escape_html(row.supplier_name || "")}
										</button>
									</td>
									<td>${this.formatNumber(row.opening)}</td>
									<td>${this.formatNumber(row.inflow)}</td>
									<td>${this.formatNumber(row.cash_payment)}</td>
									<td>${this.formatNumber(row.bank_payment)}</td>
									<td>${row.sum_balance ? this.formatLocalBalance(row.sum_balance) : ""}</td>
									<td class="${row.rentability < 0 ? "is-negative" : ""}">${this.formatPercent(row.rentability)}</td>
								</tr>
							`
						)
						.join("")}
				</tbody>
				<tfoot>
					<tr>
						<td class="is-text">Итого</td>
						<td>${this.formatNumber(totals.opening)}</td>
						<td>${this.formatNumber(totals.inflow)}</td>
						<td>${this.formatNumber(totals.cash_payment)}</td>
						<td>${this.formatNumber(totals.bank_payment)}</td>
						<td>${totals.sum_balance ? this.formatLocalBalance(totals.sum_balance) : ""}</td>
						<td class="${totals.inflow && totals.sum_balance < 0 ? "is-negative" : ""}">${this.formatPercent(totals.inflow ? (totals.sum_balance / totals.inflow) * 100 : 0)}</td>
					</tr>
				</tfoot>
			</table>
		`);

		this.$table.find("[data-supplier]").on("click", (e) => {
			const supplier = String($(e.currentTarget).data("supplier") || "");
			this.load_context({
				supplier: supplier === this.state.supplier ? null : supplier,
			});
		});
	}

	formatNumber(value) {
		if (!value) return "";
		const sign = value < 0 ? "-" : "";
		const numeric = Math.abs(Math.round(value));
		return `${sign}${String(numeric).replace(/\B(?=(\d{3})+(?!\d))/g, " ")}`;
	}

	formatLocalBalance(value) {
		if (!value) return "";
		const formatted = this.formatNumber(Math.abs(value));
		return value < 0 ? `-${formatted} сўм` : `${formatted} сўм`;
	}

	formatKpi(value, kind) {
		if (!value) {
			return "(Пусто)";
		}

		return kind === "prepayment" ? `-${this.formatNumber(value)}` : this.formatNumber(value);
	}

	formatPercent(value) {
		return `${Number(value || 0).toFixed(2).replace(".", ",")}%`;
	}

	render_loading() {
		const loadingMarkup = `<div class="supplier-dashboard-empty">${__("Загрузка...")}</div>`;
		this.$period.html("");
		this.$kpis.html(loadingMarkup);
		this.$table.html(loadingMarkup);
	}
};
