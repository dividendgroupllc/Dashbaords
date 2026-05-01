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
		this.selectedMonth = null;
		this.metricColumns = {
			check_trend: { label: "Средний чек", totalLabel: "Макс" },
			price_trend: { label: "Средняя себестоимость", totalLabel: "Макс" },
		};
		this.regionPalette = [
			"#2f87e4",
			"#2836a7",
			"#f07432",
			"#7a0f93",
			"#d63ba6",
			"#20a36e",
			"#f0c000",
			"#2e9f95",
			"#d94f45",
			"#5f7c2f",
			"#7b5cff",
			"#c86b1f",
			"#148d57",
			"#9f3f7f",
		];
		this.geoJsonPromise = null;

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
					<div class="dashboard-page-kpis" data-region="kpis"></div>
					<div class="dashboard-page-middle">
						<div class="dashboard-page-column dashboard-page-column--left">
							<div class="dashboard-page-filter-card">
								<div class="dashboard-page-filter-title">Год</div>
								<div class="dashboard-page-year-list" data-region="years"></div>
							</div>
							<div class="dashboard-page-filter-card">
								<div class="dashboard-page-filter-title">Месяц</div>
								<div class="dashboard-page-month-list" data-region="months"></div>
							</div>
						</div>
						<div class="dashboard-page-column dashboard-page-column--center">
							<div class="dashboard-page-card">
								<div class="dashboard-page-table-slot" data-table="product-margin"></div>
							</div>
						</div>
					</div>
					<div class="dashboard-page-wide-section">
						<div class="dashboard-page-card">
							<div class="dashboard-page-table-slot dashboard-page-table-slot--wide" data-table="kpi-client-monthly"></div>
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

		this.$kpis = this.page.main.find('[data-region="kpis"]');
		this.$years = this.page.main.find('[data-region="years"]');
		this.$months = this.page.main.find('[data-region="months"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.page_dashboard.page_dashboard.get_dashboard_context",
			args: {
				year: this.selectedYear,
				month: this.selectedMonth,
			},
			callback: (r) => {
				this.context = r.message || {};
				this.selectedYear = String(this.context.selected_year || this.context.default_year || this.selectedYear || "");
				this.selectedMonth = this.context.selected_month ? String(this.context.selected_month) : null;
				this.render();
			},
		});
	}

	render() {
		this.render_kpis();
		this.render_year_buttons();
		this.render_month_buttons();
		this.render_tables();
		this.render_charts();
	}

	render_kpis() {
		const kpis = this.context.kpis || [];
		const totals = this.context.kpi_totals || {};
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
				.join("")
		);

		this.$years.find(".dashboard-page-year").on("click", (e) => {
			this.selectedYear = String($(e.currentTarget).data("year"));
			this.selectedMonth = null;
			this.load_context();
		});
	}

	render_month_buttons() {
		const months = this.context.months || [];
		this.$months.html(
			months
				.map(
					(month) => `
						<button class="dashboard-page-month ${month === this.selectedMonth ? "is-active" : ""}" data-month="${month}">
							<span class="dashboard-page-month-mark"></span>
							${frappe.utils.escape_html(month)}
						</button>
					`
				)
				.join("")
		);

		this.$months.find(".dashboard-page-month").on("click", (e) => {
			const month = String($(e.currentTarget).data("month"));
			this.selectedMonth = month === this.selectedMonth ? null : month;
			this.load_context();
		});
	}

	render_tables() {
		this.render_table(
			"product-margin",
			this.context.product_margin_rows || [],
			["Товары", "Тонна", "Сумма продаж", "RCP сумма", "Маржа", "Рен"],
			this.context.product_margin_title || null
		);
		this.render_table(
			"kpi-client-monthly",
			this.context.kpi_client_rows || [],
			["Клиент", "Продажа", "Сб.ст", "КГ", "Возврат", "Маржа", "%", "Бонус", "Скидка", "Маржа нет", "PnL"],
			this.context.kpi_client_title || null
		);
		this.render_table(
			"regional-summary",
			this.context.regional_summary_rows || [],
			["Город", "Сумма", "Маржа", "Рен"]
		);
	}

	render_table(key, rows, headers, title = null) {
		const $slot = this.page.main.find(`[data-table="${key}"]`);
		if (key === "regional-summary") {
			this.render_region_map($slot, this.context.regional_map || []);
			return;
		}
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
											const shouldShorten = (key === "client-kpi" || key === "kpi-client-monthly") && index === 0;
											const cellValue = shouldShorten ? this.shorten_label(rawValue, key === "kpi-client-monthly" ? 28 : 22) : rawValue;
											const titleAttr =
												shouldShorten
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
			"product-margin": ["32%", "12%", "18%", "14%", "14%", "10%"],
			"client-kpi": ["34%", "16%", "32%", "18%"],
			"kpi-client-monthly": ["18%", "9%", "9%", "7%", "9%", "9%", "6%", "9%", "8%", "10%", "6%"],
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

	normalize_region_label(value) {
		return String(value || "")
			.toLowerCase()
			.normalize("NFKD")
			.replace(/[\u0300-\u036f]/g, "")
			.replace(/[ʻʼ’`']/g, "")
			.replace(/\s+/g, " ")
			.replace(/\b(viloyati|region|province|oblast|область|respublikasi|republic|city|sh)\b/g, "")
			.replace(/\./g, "")
			.trim();
	}

	isTerritoryPlaceholder(value) {
		const normalized = this.normalize_region_label(value);
		return (
			!normalized ||
			normalized === "bez territorii" ||
			normalized === "bez territoriy" ||
			normalized === "без территории" ||
			normalized === "no territory"
		);
	}

	load_geojson() {
		if (!this.geoJsonPromise) {
			this.geoJsonPromise = new Promise((resolve, reject) => {
				frappe.call({
					method: "dashboards.dashboards.page.page_dashboard.page_dashboard.get_regions_geojson",
					callback: (r) => resolve(r.message || {}),
					error: (err) => reject(err || new Error("GeoJSON API failed")),
				});
			});
		}
		return this.geoJsonPromise;
	}

	projectCoordinate(coord) {
		const [lon, lat] = coord;
		const lambda = (lon * Math.PI) / 180;
		const phi = Math.max(-Math.PI / 2 + 1e-6, Math.min(Math.PI / 2 - 1e-6, (lat * Math.PI) / 180));
		return [lambda, Math.log(Math.tan(Math.PI / 4 + phi / 2))];
	}

	extractRings(geometry) {
		if (!geometry || !geometry.type || !geometry.coordinates) {
			return [];
		}
		if (geometry.type === "Polygon") {
			return geometry.coordinates || [];
		}
		if (geometry.type === "MultiPolygon") {
			return (geometry.coordinates || []).flat();
		}
		return [];
	}

	computeProjection(geojson, width, height, padding = 18) {
		const features = geojson.features || [];
		const bounds = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
		features.forEach((feature) => {
			this.extractRings(feature.geometry).forEach((ring) => {
				(ring || []).forEach((coord) => {
					const [x, y] = this.projectCoordinate(coord);
					bounds.minX = Math.min(bounds.minX, x);
					bounds.minY = Math.min(bounds.minY, y);
					bounds.maxX = Math.max(bounds.maxX, x);
					bounds.maxY = Math.max(bounds.maxY, y);
				});
			});
		});

		const spanX = Math.max(bounds.maxX - bounds.minX, 1e-9);
		const spanY = Math.max(bounds.maxY - bounds.minY, 1e-9);
		const scale = Math.min((width - padding * 2) / spanX, (height - padding * 2) / spanY);
		const offsetX = (width - spanX * scale) / 2 - bounds.minX * scale;
		const offsetY = (height - spanY * scale) / 2 + bounds.maxY * scale;

		return {
			project: (coord) => {
				const [x, y] = this.projectCoordinate(coord);
				return [x * scale + offsetX, offsetY - y * scale];
			},
		};
	}

	ringsToPath(rings, project) {
		return (rings || [])
			.map((ring) => {
				const points = (ring || []).map(project);
				if (!points.length) {
					return "";
				}
				const [firstX, firstY] = points[0];
				const segments = points.slice(1).map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`).join("");
				return `M${firstX.toFixed(2)},${firstY.toFixed(2)}${segments}Z`;
			})
			.join(" ");
	}

	computePolygonCentroid(ring, project) {
		const points = (ring || []).map(project);
		if (points.length < 3) {
			return points[0] || [0, 0];
		}

		let area = 0;
		let cx = 0;
		let cy = 0;
		for (let i = 0; i < points.length - 1; i++) {
			const [x1, y1] = points[i];
			const [x2, y2] = points[i + 1];
			const cross = x1 * y2 - x2 * y1;
			area += cross;
			cx += (x1 + x2) * cross;
			cy += (y1 + y2) * cross;
		}

		if (Math.abs(area) < 1e-9) {
			const sum = points.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
			return [sum[0] / points.length, sum[1] / points.length];
		}

		return [cx / (3 * area), cy / (3 * area)];
	}

	computeFeatureCentroid(feature, project) {
		const rings = this.extractRings(feature.geometry);
		return this.computePolygonCentroid(rings[0] || [], project);
	}

	computeFeatureArea(feature, project) {
		const rings = this.extractRings(feature.geometry);
		const ring = rings[0] || [];
		const points = ring.map(project);
		let area = 0;
		for (let i = 0; i < points.length - 1; i++) {
			const [x1, y1] = points[i];
			const [x2, y2] = points[i + 1];
			area += x1 * y2 - x2 * y1;
		}
		return Math.abs(area / 2);
	}

	build_region_feature_lookup(geojson) {
		const lookup = new Map();
		(geojson.features || []).forEach((feature) => {
			const props = feature.properties || {};
			[
				props.name,
				props.name_en,
				props.name_ru,
				props.name_uz,
				props.slug,
				String(props.name_uz || "").replace(/\s+viloyati$/i, ""),
				String(props.name || "").replace(/\s+Respublikasi$/i, ""),
			]
				.filter(Boolean)
				.forEach((value) => lookup.set(this.normalize_region_label(value), feature));
		});
		return lookup;
	}

	formatDecimal(value, digits = 1) {
		return new Intl.NumberFormat("ru-RU", {
			minimumFractionDigits: digits,
			maximumFractionDigits: digits,
		}).format(Number(value || 0));
	}

	getRegionFillColor(name, row, rankedRows) {
		if (!row) {
			return "#dbe3ea";
		}
		const index = rankedRows.findIndex((item) => this.normalize_region_label(item.territory) === this.normalize_region_label(name));
		return this.regionPalette[(index >= 0 ? index : 0) % this.regionPalette.length];
	}

	render_region_map($slot, rows) {
		$slot.html(`
			<div class="dashboard-page-map-card">
				<div class="dashboard-page-map-title">Город</div>
				<div class="dashboard-page-map-board">
					<div class="dashboard-page-map-canvas">
						<svg class="dashboard-page-map-svg" data-region="geo-map" aria-label="Uzbekistan regional sales map"></svg>
						<div class="dashboard-page-map-tooltip" data-region="map-tooltip"></div>
					</div>
				</div>
				<div class="dashboard-page-map-unmatched" data-region="map-unmatched"></div>
			</div>
		`);

		this.load_geojson()
			.then((geojson) => {
				const $canvas = $slot.find(".dashboard-page-map-canvas");
				const $tooltip = $slot.find('[data-region="map-tooltip"]');
				const $unmatched = $slot.find('[data-region="map-unmatched"]');
				const svgEl = $slot.find('[data-region="geo-map"]')[0];
				const width = Math.max($canvas.innerWidth() || 0, 420);
				const height = Math.max($canvas.innerHeight() || 0, 290);
				const rowLookup = new Map((rows || []).map((row) => [this.normalize_region_label(row.territory), row]));
				const featureLookup = this.build_region_feature_lookup(geojson);
				const matchedRows = [];
				const unmatched = [];

				(rows || []).forEach((row) => {
					const feature = featureLookup.get(this.normalize_region_label(row.territory));
					if (feature) {
						matchedRows.push(row);
						return;
					}
					unmatched.push(row);
				});

					const visibleUnmatched = unmatched.filter((row) => !this.isTerritoryPlaceholder(row.territory));
					$unmatched.text(
						visibleUnmatched.length
							? visibleUnmatched.map((row) => `${row.territory}: ${this.formatInteger(row.sales)}`).join(" · ")
							: ""
					);

				svgEl.innerHTML = "";
				svgEl.setAttribute("viewBox", `0 0 ${width} ${height}`);
				svgEl.setAttribute("preserveAspectRatio", "xMidYMid meet");
				const projection = this.computeProjection(geojson, width, height, 18);
					const rankedRows = [...matchedRows].sort((a, b) => Number(b.sales || 0) - Number(a.sales || 0));

					(geojson.features || []).forEach((feature) => {
						const name = (feature.properties || {}).name || "";
						const row = rowLookup.get(this.normalize_region_label(name));
					const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
					group.setAttribute("class", `dashboard-page-map-region ${row ? "has-data" : "is-muted"}`);

						const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
						pathEl.setAttribute("class", "dashboard-page-map-path");
						pathEl.setAttribute("d", this.ringsToPath(this.extractRings(feature.geometry), projection.project));
						pathEl.setAttribute("fill", this.getRegionFillColor(name, row, rankedRows));
					pathEl.setAttribute("stroke", "#6d8492");
					pathEl.setAttribute("stroke-width", "1.2");
					pathEl.setAttribute("stroke-linejoin", "round");

					const [cx, cy] = this.computeFeatureCentroid(feature, projection.project);
					const textEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
					textEl.setAttribute("class", "dashboard-page-map-label");
					textEl.setAttribute("x", String(cx));
					textEl.setAttribute("y", String(cy));
					textEl.setAttribute("dy", "0.35em");
					textEl.style.fontSize = `${Math.max(9, Math.min(16, Math.sqrt(this.computeFeatureArea(feature, projection.project)) / 10))}px`;
					textEl.textContent = name;

					group.appendChild(pathEl);
					group.appendChild(textEl);
					group.addEventListener("mouseenter", (event) => {
						$tooltip.html(`
							<div class="dashboard-page-map-tooltip-title">${frappe.utils.escape_html(name)}</div>
							<div>Продажа: ${frappe.utils.escape_html(this.formatInteger((row || {}).sales || 0))}</div>
							<div>Тонна: ${frappe.utils.escape_html(this.formatDecimal((row || {}).tons || 0, 1))} t</div>
							<div>AKB: ${frappe.utils.escape_html(this.formatInteger((row || {}).akb || 0))}</div>
						`);
						$tooltip.addClass("is-visible");
						const offset = $slot.offset() || { left: 0, top: 0 };
						$tooltip.css({ left: `${event.pageX - offset.left + 16}px`, top: `${event.pageY - offset.top - 12}px` });
					});
					group.addEventListener("mousemove", (event) => {
						const offset = $slot.offset() || { left: 0, top: 0 };
						$tooltip.css({ left: `${event.pageX - offset.left + 16}px`, top: `${event.pageY - offset.top - 12}px` });
					});
					group.addEventListener("mouseleave", () => {
						$tooltip.removeClass("is-visible");
					});
					group.addEventListener("click", () => {
						console.log("Uzbekistan region:", name);
					});
					svgEl.appendChild(group);
				});
			})
			.catch((error) => {
				console.error(error);
				const message =
					(error && (error.message || error.exc || error.exception || error.statusText)) ||
					(typeof error === "string" ? error : "") ||
					"Unknown map error";
				$slot.find(".dashboard-page-map-canvas").html(
					`<div class="dashboard-page-map-error">GeoJSON map load failed: ${frappe.utils.escape_html(message)}</div>`
				);
			});
	}

	render_charts() {
		const yearCharts = this.context.chart_data || {};
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
		const differenceValues = rows.map((row) => row.metrics.check_trend.value - row.metrics.price_trend.value);
		const differenceMax = this.getMetricTotal("Макс", differenceValues);

		$container.html(`
			<div class="dashboard-page-month-metrics">
				<div class="dashboard-page-month-metrics-head">
					<div class="is-month">${__("Месяц")}</div>
					<div class="is-metric">${frappe.utils.escape_html(this.metricColumns.price_trend.label)}</div>
					<div class="is-metric">${frappe.utils.escape_html(this.metricColumns.check_trend.label)}</div>
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
									<div class="is-metric">${frappe.utils.escape_html(this.formatInteger(row.metrics.price_trend.value))}</div>
									<div class="is-metric">${frappe.utils.escape_html(this.formatInteger(row.metrics.check_trend.value))}</div>
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
						<div class="dashboard-page-month-metrics-total-label">${frappe.utils.escape_html(this.metricColumns.price_trend.totalLabel)}</div>
						<div>${frappe.utils.escape_html(this.formatInteger(totals.price_trend))}</div>
					</div>
					<div class="is-metric">
						<div class="dashboard-page-month-metrics-total-label">${frappe.utils.escape_html(this.metricColumns.check_trend.totalLabel)}</div>
						<div>${frappe.utils.escape_html(this.formatInteger(totals.check_trend))}</div>
					</div>
					<div class="is-metric">
						<div class="dashboard-page-month-metrics-total-label">${frappe.utils.escape_html("Макс")}</div>
						<div>${frappe.utils.escape_html(this.formatInteger(differenceMax))}</div>
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
