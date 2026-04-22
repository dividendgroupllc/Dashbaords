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
							<div class="kpi-dashboard-subtitle" data-region="client-table-title"></div>
							<div class="kpi-dashboard-table-wrap kpi-dashboard-table-wrap--monthly" data-region="client-table"></div>
						</div>
						<div class="kpi-dashboard-bottom">
							<div class="kpi-dashboard-card">
								<div class="kpi-dashboard-subtitle" data-region="summary-table-title"></div>
								<div class="kpi-dashboard-table-wrap kpi-dashboard-table-wrap--yearly" data-region="summary-table"></div>
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

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "kpi-dashboard",
		});

		this.$years = this.page.main.find('[data-region="years"]');
		this.$months = this.page.main.find('[data-region="months"]');
		this.$kpis = this.page.main.find('[data-region="kpis"]');
		this.$caption = this.page.main.find('[data-region="caption"]');
		this.$clientTableTitle = this.page.main.find('[data-region="client-table-title"]');
		this.$clientTable = this.page.main.find('[data-region="client-table"]');
		this.$summaryTableTitle = this.page.main.find('[data-region="summary-table-title"]');
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
		this.$clientTableTitle.text(`${this.selectedMonth || ""} ${this.selectedYear || ""} oylik ma'lumot`);
		this.$clientTable.html(this.make_table(headers, this.data.client_rows || [], "wide"));
	}

	render_summary_table() {
		const headers = ["Клиент", "Продажа", "Сб.ст", "КГ", "Возврат", "Маржа", "%", "Бонус", "Скидка", "Маржа нет", "PnL"];
		this.$summaryTableTitle.text(`${this.selectedYear || ""} yillik ma'lumot`);
		this.$summaryTable.html(this.make_table(headers, this.data.summary_rows || [], "wide"));
	}

	make_table(headers, rows, variant) {
		const widths = this.get_column_widths(variant, headers.length);
		const colgroup = widths.length
			? `<colgroup>${widths.map((width) => `<col style="width:${width}">`).join("")}</colgroup>`
			: "";
		const totalRow = rows.find((row) => row[row.length - 1] === true) || null;
		const bodyRows = rows.filter((row) => row[row.length - 1] !== true);

		const renderRow = (row, extraClass = "") => {
			const isTotal = row[row.length - 1] === true;
			const values = isTotal ? row.slice(0, -1) : row;
			return `
				<tr class="${extraClass}">
					${values
						.map((value, index) => {
							const alignClass = index === 0 ? "is-text" : "is-number";
							return `<td class="${alignClass}">${frappe.utils.escape_html(String(value))}</td>`;
						})
						.join("")}
				</tr>
			`;
		};

		return `
			<table class="kpi-dashboard-table kpi-dashboard-table--${variant}">
				${colgroup}
				<thead>
					<tr>${headers.map((header) => `<th>${frappe.utils.escape_html(header)}</th>`).join("")}</tr>
				</thead>
				<tbody>
					${bodyRows.map((row) => renderRow(row)).join("")}
				</tbody>
				${totalRow ? `<tfoot>${renderRow(totalRow, "is-total")}</tfoot>` : ""}
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

	compute_treemap_layout(items) {
		const width = Math.max(this.$treemap.innerWidth() || 0, 1);
		const height = Math.max(this.$treemap.innerHeight() || 0, 1);
		const totalArea = width * height;
		const total = items.reduce((sum, item) => sum + Number(item.net_profit_margin_amount || 0), 0) || 1;
		const normalized = items
			.filter((item) => Number(item.net_profit_margin_amount || 0) > 0)
			.map((item) => ({
				...item,
				net_profit_margin_amount: Number(item.net_profit_margin_amount || 0),
				area: Number(item.net_profit_margin_amount || 0) / total,
				size: (Number(item.net_profit_margin_amount || 0) / total) * totalArea,
			}))
			.filter((item) => item.size > 0);

		if (!normalized.length) {
			return [];
		}

		const shortest = (rect) => Math.min(rect.width, rect.height);
		const worst = (row, side) => {
			if (!row.length || !side) {
				return Number.POSITIVE_INFINITY;
			}

			const areas = row.map((item) => item.size);
			const sum = areas.reduce((acc, area) => acc + area, 0);
			const max = Math.max(...areas);
			const min = Math.min(...areas);

			if (!min || !sum) {
				return Number.POSITIVE_INFINITY;
			}

			const sideSquared = side * side;
			const sumSquared = sum * sum;
			return Math.max((sideSquared * max) / sumSquared, sumSquared / (sideSquared * min));
		};

		const layoutRow = (row, rect) => {
			const rowArea = row.reduce((sum, item) => sum + item.size, 0);
			const output = [];

			// Pack each row along the shorter side. On wide containers this creates columns,
			// which avoids the "stacked horizontal strips" failure mode.
			if (rect.width >= rect.height) {
				const rowWidth = rect.height ? rowArea / rect.height : 0;
				let offsetY = rect.y;
				row.forEach((item) => {
					const itemHeight = rowWidth ? item.size / rowWidth : 0;
					output.push({
						...item,
						x: rect.x,
						y: offsetY,
						width: rowWidth,
						height: itemHeight,
					});
					offsetY += itemHeight;
				});
				return {
					rect: {
						x: rect.x + rowWidth,
						y: rect.y,
						width: Math.max(rect.width - rowWidth, 0),
						height: rect.height,
					},
					tiles: output,
				};
			}

			const rowHeight = rect.width ? rowArea / rect.width : 0;
			let offsetX = rect.x;
			row.forEach((item) => {
				const itemWidth = rowHeight ? item.size / rowHeight : 0;
				output.push({
					...item,
					x: offsetX,
					y: rect.y,
					width: itemWidth,
					height: rowHeight,
				});
				offsetX += itemWidth;
			});

			return {
				rect: {
					x: rect.x,
					y: rect.y + rowHeight,
					width: rect.width,
					height: Math.max(rect.height - rowHeight, 0),
				},
				tiles: output,
			};
		};

		let rect = { x: 0, y: 0, width, height };
		let row = [];
		let remaining = [...normalized];
		const tiles = [];

		while (remaining.length) {
			const next = remaining[0];
			const side = shortest(rect);
			const nextRow = [...row, next];

			if (!row.length || worst(nextRow, side) <= worst(row, side)) {
				row = nextRow;
				remaining.shift();
				continue;
			}

			const result = layoutRow(row, rect);
			tiles.push(...result.tiles);
			rect = result.rect;
			row = [];
		}

		if (row.length) {
			const result = layoutRow(row, rect);
			tiles.push(...result.tiles);
		}

		return tiles.map((item) => ({
			...item,
			x: item.x / width,
			y: item.y / height,
			width: item.width / width,
			height: item.height / height,
		}));
	}

	render_treemap() {
		const items = this.data.treemap || [];
		const palette = ["#2f87e4", "#2836a7", "#f07432", "#7a0f93", "#d63ba6", "#7251c7", "#f0c000", "#20a36e"];
		const formatNumber = (value) => new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Number(value || 0));
		const total = items.reduce((sum, item) => sum + Number(item.net_profit_margin_amount || 0), 0) || 1;
		const tiles = this.compute_treemap_layout(items);

		this.$treemap.html(
			tiles
				.map((item, index) => {
					const areaPercent = item.area * 100;
					const compactClass = areaPercent < 8 ? "is-compact" : "";
					const tinyClass = areaPercent < 4 ? "is-tiny" : "";
					const displayLabel = item.client_name || "";
					const fontSize = Math.max(10, Math.min(24, Math.round(Math.sqrt(areaPercent) * 2.2)));
					return `
						<div
							class="kpi-dashboard-treemap-item ${compactClass} ${tinyClass}"
							style="
								left:${(item.x * 100).toFixed(4)}%;
								top:${(item.y * 100).toFixed(4)}%;
								width:${(item.width * 100).toFixed(4)}%;
								height:${(item.height * 100).toFixed(4)}%;
								background:${palette[index % palette.length]};
							"
							title="${frappe.utils.escape_html(displayLabel)}: ${frappe.utils.escape_html(
								formatNumber(item.net_profit_margin_amount)
							)}"
						>
							<div class="kpi-dashboard-treemap-name" style="font-size:${fontSize}px">${frappe.utils.escape_html(displayLabel)}</div>
						</div>
					`;
				})
				.join("")
		);
	}
};
