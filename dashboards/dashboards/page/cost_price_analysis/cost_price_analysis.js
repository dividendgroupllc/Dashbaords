frappe.pages["cost-price-analysis"].on_page_load = function (wrapper) {
	new dashboards.ui.CostPriceAnalysisPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.CostPriceAnalysisPage = class CostPriceAnalysisPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Себестоимость продукции"),
			single_column: true,
		});

		this.state = {
			year: null,
			item_group: null,
		};
		this.view = {
			search: "",
			sort: "name",
		};
		this.context = {};

		this.make_layout();
		this.bind_events();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("cost-price-analysis-layout");
		this.wrapper.find(".page-head").addClass("cost-price-analysis-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="cpa-screen">
				<div class="cpa-main">
					<section class="cpa-filters">
						<div class="cpa-field">
							<label class="cpa-field-label" for="cpa-year">Год</label>
							<select class="cpa-input" id="cpa-year" data-region="year"></select>
						</div>
						<div class="cpa-field">
							<label class="cpa-field-label" for="cpa-group">Группа товаров</label>
							<select class="cpa-input" id="cpa-group" data-region="group"></select>
						</div>
						<div class="cpa-field cpa-field--search">
							<label class="cpa-field-label" for="cpa-search">Поиск товара</label>
							<input class="cpa-input" id="cpa-search" type="search" placeholder="Название товара" data-region="search" />
						</div>
						<div class="cpa-filter-tail">
							<div class="cpa-field">
								<span class="cpa-field-label">Сортировка</span>
								<div class="cpa-chips" data-region="sort">
									<button class="cpa-chip is-active" type="button" data-sort="name">По названию</button>
									<button class="cpa-chip" type="button" data-sort="rise">Рост</button>
									<button class="cpa-chip" type="button" data-sort="fall">Снижение</button>
									<button class="cpa-chip" type="button" data-sort="cost">Цена</button>
								</div>
							</div>
							<div class="cpa-field cpa-field--action">
								<span class="cpa-field-label">&nbsp;</span>
								<button class="cpa-export" type="button" data-region="export">Выгрузить Excel</button>
							</div>
						</div>
					</section>

					<section class="cpa-panel">
						<div class="cpa-table-wrap" data-region="table"></div>
					</section>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "cost-price-analysis",
		});

		this.$year = this.page.main.find('[data-region="year"]');
		this.$group = this.page.main.find('[data-region="group"]');
		this.$search = this.page.main.find('[data-region="search"]');
		this.$sort = this.page.main.find('[data-region="sort"]');
		this.$export = this.page.main.find('[data-region="export"]');
		this.$table = this.page.main.find('[data-region="table"]');
	}

	bind_events() {
		this.$year.on("change", (event) => {
			this.load_context({ year: String($(event.currentTarget).val() || "") });
		});

		this.$group.on("change", (event) => {
			this.load_context({ item_group: String($(event.currentTarget).val() || "") || null });
		});

		this.$sort.on("click", "[data-sort]", (event) => {
			this.view.sort = String($(event.currentTarget).data("sort") || "name");
			this.$sort.find("[data-sort]").removeClass("is-active");
			$(event.currentTarget).addClass("is-active");
			this.render_table();
		});

		this.$search.on(
			"input",
			frappe.utils.debounce(() => {
				this.view.search = String(this.$search.val() || "").trim().toLowerCase();
				this.render_table();
			}, 200)
		);

		this.$export.on("click", () => this.export_xlsx());
	}

	load_context(filters = {}) {
		this.render_loading();

		frappe.call({
			method: "dashboards.dashboards.page.cost_price_analysis.cost_price_analysis.get_dashboard_context",
			args: {
				year: Object.prototype.hasOwnProperty.call(filters, "year") ? filters.year : this.state.year,
				item_group: Object.prototype.hasOwnProperty.call(filters, "item_group")
					? filters.item_group
					: this.state.item_group,
			},
			callback: (r) => {
				this.context = r.message || {};
				this.state = { ...this.state, ...(this.context.default_filters || {}) };
				this.render();
			},
		});
	}

	render() {
		this.render_filters();
		this.render_table();
	}

	render_filters() {
		this.$year.html(
			(this.context.years || [])
				.map(
					(year) =>
						`<option value="${frappe.utils.escape_html(String(year))}" ${
							String(year) === String(this.state.year) ? "selected" : ""
						}>${frappe.utils.escape_html(String(year))}</option>`
				)
				.join("")
		);

		this.$group.html(
			[`<option value="">Все группы</option>`]
				.concat(
					(this.context.item_groups || []).map(
						(group) =>
							`<option value="${frappe.utils.escape_html(group)}" ${
								group === this.state.item_group ? "selected" : ""
							}>${frappe.utils.escape_html(group)}</option>`
					)
				)
				.join("")
		);
	}

	visible_rows() {
		let rows = (this.context.rows || []).slice();

		if (this.view.search) {
			rows = rows.filter(
				(row) =>
					String(row.item_name || "").toLowerCase().includes(this.view.search) ||
					String(row.item_code || "").toLowerCase().includes(this.view.search)
			);
		}

		// Обычное сравнение строк в нижнем регистре, а не localeCompare: ровно то же
		// правило применяет apply_view() в data.py, поэтому порядок строк в выгрузке
		// Excel совпадает с порядком на экране.
		const byName = (a, b) => {
			const left = String(a.item_name || "").toLowerCase();
			const right = String(b.item_name || "").toLowerCase();
			return left < right ? -1 : left > right ? 1 : 0;
		};
		const change = (row) => (row.year_change === null || row.year_change === undefined ? 0 : row.year_change);

		if (this.view.sort === "rise") {
			rows.sort((a, b) => change(b) - change(a) || byName(a, b));
		} else if (this.view.sort === "fall") {
			rows.sort((a, b) => change(a) - change(b) || byName(a, b));
		} else if (this.view.sort === "cost") {
			rows.sort((a, b) => Number(b.avg || 0) - Number(a.avg || 0) || byName(a, b));
		} else {
			rows.sort(byName);
		}

		return rows;
	}

	render_table() {
		const months = this.context.months || [];
		const rows = this.visible_rows();

		if (!rows.length) {
			this.$table.html(`<div class="cpa-empty">Данные не найдены.</div>`);
			return;
		}

		// Ширина колонок задаётся в процентах, а таблица — table-layout: fixed,
		// поэтому все 12 месяцев всегда помещаются в экран без горизонтальной
		// прокрутки. Месяцы без данных сжимаются, отдавая ширину активным.
		const idleCount = months.filter((month) => !month.is_active).length;
		const activeCount = months.length - idleCount;
		const nameWidth = 19;
		const idleWidth = 3.6;
		const activeWidth = activeCount ? (100 - nameWidth - idleCount * idleWidth) / activeCount : idleWidth;

		const colgroup = `
			<colgroup>
				<col style="width:${nameWidth}%" />
				${months
					.map((month) => `<col style="width:${(month.is_active ? activeWidth : idleWidth).toFixed(3)}%" />`)
					.join("")}
			</colgroup>
		`;

		const header = `
			<tr>
				<th class="cpa-name-col">Товар</th>
				${months
					.map(
						(month) =>
							`<th class="cpa-month-col ${month.is_active ? "" : "is-idle"}" title="${frappe.utils.escape_html(
								month.full
							)}">${frappe.utils.escape_html(month.label)}</th>`
					)
					.join("")}
			</tr>
		`;

		const body = rows
			.map(
				(row) => `
					<tr>
						<td class="cpa-name-cell">
							<div class="cpa-item-name">${frappe.utils.escape_html(row.item_name || "")}</div>
							<div class="cpa-item-meta">${frappe.utils.escape_html(row.item_group || "")}${
								row.uom ? ` • ${frappe.utils.escape_html(this.context.currency || "")}/${frappe.utils.escape_html(row.uom)}` : ""
							}</div>
						</td>
						${(row.cells || []).map((cell) => this.render_cell(cell)).join("")}
					</tr>
				`
			)
			.join("");

		this.$table.html(`
			<table class="cpa-table">
				${colgroup}
				<thead>${header}</thead>
				<tbody>${body}</tbody>
			</table>
		`);
	}

	render_cell(cell) {
		if (!cell) {
			return `<td class="cpa-cell is-empty"></td>`;
		}

		const classes = ["cpa-cell", `is-${cell.direction || "none"}`];
		if (cell.carried) {
			classes.push("is-carried");
		}

		const changeMarkup =
			cell.change_display && cell.direction !== "none" && cell.direction !== "flat"
				? `<div class="cpa-cell-change">${this.arrow(cell.direction)}${frappe.utils.escape_html(cell.change_display)}</div>`
				: "";

		return `
			<td class="${classes.join(" ")}">
				<div class="cpa-cell-value">${frappe.utils.escape_html(cell.display || "")}</div>
				${changeMarkup}
			</td>
		`;
	}

	arrow(direction) {
		if (direction === "up") {
			return "▲ ";
		}
		if (direction === "down") {
			return "▼ ";
		}
		return "";
	}

	export_xlsx() {
		if (!this.visible_rows().length) {
			frappe.show_alert({ message: __("Нечего выгружать"), indicator: "orange" });
			return;
		}

		// Книгу собирает сервер (openpyxl): числа остаются числами, а заливка
		// повторяет цвета экрана. Фильтры передаём те же, что применены к таблице.
		const params = new URLSearchParams({
			year: this.state.year || "",
			item_group: this.state.item_group || "",
			search: this.view.search || "",
			sort: this.view.sort || "name",
		});

		window.open(
			`/api/method/dashboards.dashboards.page.cost_price_analysis.cost_price_analysis.export_xlsx?${params.toString()}`
		);
	}

	render_loading() {
		this.$table.html(`<div class="cpa-empty">Загрузка...</div>`);
	}
};
