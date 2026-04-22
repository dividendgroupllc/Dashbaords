frappe.pages["main-dashboard"].on_page_load = function (wrapper) {
	new dashboards.ui.MainDashboardPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.MainDashboardPage = class MainDashboardPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Main Dashboard"),
			single_column: true,
		});

		this.widget_names = {
			main_chart: "Main Dashboard Timeline",
			mini_chart: "Main Dashboard Monthly Snapshot",
			sales_amount: "Main Dashboard Sales Amount",
			sales_kg: "Main Dashboard Sales Kg",
			cash_total: "Main Dashboard Cash Total",
			bank_total: "Main Dashboard Bank Total",
			collections_total: "Main Dashboard Collections",
			debtor_total: "Main Dashboard Debtor Total",
			avg_price: "Main Dashboard Average Price",
			avg_cost: "Main Dashboard Average Cost",
			dividend_total: "Main Dashboard Dividend Total",
		};

		this.make_layout();
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("main-dashboard-layout");
		this.page.main.removeClass("frappe-card");
		this.wrapper.find(".page-head").addClass("main-dashboard-page-head");

		this.page.main.html(`
			<div class="main-dashboard-screen">
				<div class="main-dashboard-panel">
					<div class="main-dashboard-tabs" data-region="tabs"></div>
					<div class="main-dashboard-chart main-dashboard-chart--primary" data-region="main-chart"></div>
					<div class="main-dashboard-bottom">
						<div class="main-dashboard-mini-chart">
							<div class="main-dashboard-section-label">Месячная динамика</div>
							<div data-region="mini-chart"></div>
						</div>
						<div class="main-dashboard-summary">
							<div class="main-dashboard-summary-table" data-region="summary-table"></div>
						</div>
						<div class="main-dashboard-side">
							<div class="main-dashboard-side-metrics" data-region="side-metrics"></div>
							<div class="main-dashboard-dividend">
								<div data-region="dividend-card"></div>
								<div class="main-dashboard-dividend-label" data-region="balance-label">${__("Сальдо на конец")}</div>
								<div class="main-dashboard-dividend-update-label">${__("Последнее обновление")}</div>
								<div class="main-dashboard-dividend-update-time" data-region="updated-at"></div>
							</div>
						</div>
					</div>
					<div class="main-dashboard-footer" data-region="footer-ticker"></div>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "main-dashboard",
		});

		this.$tabs = this.page.main.find('[data-region="tabs"]');
		this.$mainChart = this.page.main.find('[data-region="main-chart"]');
		this.$miniChart = this.page.main.find('[data-region="mini-chart"]');
		this.$summaryTable = this.page.main.find('[data-region="summary-table"]');
		this.$sideMetrics = this.page.main.find('[data-region="side-metrics"]');
		this.$dividendCard = this.page.main.find('[data-region="dividend-card"]');
		this.$balanceLabel = this.page.main.find('[data-region="balance-label"]');
		this.$updatedAt = this.page.main.find('[data-region="updated-at"]');
		this.$footerTicker = this.page.main.find('[data-region="footer-ticker"]');
	}

	load_context() {
		frappe.call({
			method: "dashboards.dashboards.page.main_dashboard.main_dashboard.get_dashboard_context",
			callback: (r) => {
				this.context = r.message || {};
				this.render_static_regions();
				this.render_widgets();
			},
		});
	}

	render_static_regions() {
		this.render_tabs();
		this.render_main_timeline();
		this.render_mini_timeline();
		this.render_summary_table();
		this.render_side_metrics();
		this.render_footer();
		this.$balanceLabel.text(this.context.balance_label || __("Сальдо на конец"));
		this.$updatedAt.text(this.context.dividend_updated_at || "");
	}

	render_tabs() {
		const tabs = this.context.tabs || [];
		this.$tabs.html(
			tabs
				.map(
					(tab) => `
						<button class="main-dashboard-tab ${tab.active ? "is-active" : ""}" data-route="${tab.route}">
							${frappe.utils.escape_html(tab.label)}
						</button>
					`
				)
				.join("")
		);

		this.$tabs.find(".main-dashboard-tab").on("click", (e) => {
			const route = $(e.currentTarget).data("route");
			if (route) {
				frappe.set_route(route.replace(/^\/app\//, ""));
			}
		});
	}

	render_summary_table() {
		const rows = this.context.summary_rows || [];
		this.$summaryTable.html(
			rows
				.map(
					(row) => `
						<div class="main-dashboard-summary-row">
							<div class="main-dashboard-summary-title">${frappe.utils.escape_html(row.label)}</div>
							<div class="main-dashboard-summary-metrics">
								${row.metric_keys
									.map(
										(metricKey, index) => `
											<div class="main-dashboard-summary-metric">
												<div class="main-dashboard-number-slot" data-number-card="${metricKey}"></div>
												<div class="main-dashboard-summary-caption">${frappe.utils.escape_html(
													row.metric_labels[index]
												)}</div>
											</div>
										`
									)
									.join("")}
							</div>
						</div>
					`
				)
				.join("")
		);
	}

	render_side_metrics() {
		const items = this.context.side_metrics || [];
		this.$sideMetrics.html(
			items
				.map(
					(item) => `
						<div class="main-dashboard-side-metric">
							<div class="main-dashboard-side-number" data-number-card="${item.metric_key}"></div>
							<div class="main-dashboard-side-label">${frappe.utils.escape_html(item.label)}</div>
						</div>
					`
				)
				.join("")
		);
	}

	render_footer() {
		const items = this.context.footer_items || [];
		if (!items.length) {
			this.$footerTicker.empty();
			return;
		}

		const renderItem = (item) => `
			<div class="main-dashboard-footer-item">
				<span class="main-dashboard-footer-label">${frappe.utils.escape_html(item.label || "")}</span>
				<span class="main-dashboard-footer-value">${this.formatNumber(item.value)}</span>
			</div>
		`;

		const groupMarkup = items.map(renderItem).join("");
		this.$footerTicker.html(`
			<div class="main-dashboard-footer-track">
				<div class="main-dashboard-footer-group">${groupMarkup}</div>
				<div class="main-dashboard-footer-group" aria-hidden="true">${groupMarkup}</div>
			</div>
		`);

		this.setup_footer_ticker(items, renderItem);
	}

	setup_footer_ticker(items, renderItem) {
		window.requestAnimationFrame(() => {
			const $track = this.$footerTicker.find(".main-dashboard-footer-track");
			const $groups = $track.find(".main-dashboard-footer-group");
			if (!$track.length || !$groups.length) {
				return;
			}

			const containerWidth = this.$footerTicker.innerWidth() || 0;
			let groupWidth = $groups.first().outerWidth(true) || 0;

			if (containerWidth && groupWidth && groupWidth < containerWidth * 1.25) {
				const repeatCount = Math.max(2, Math.ceil((containerWidth * 1.25) / groupWidth));
				const repeatedMarkup = Array.from({ length: repeatCount }, () => items)
					.flat()
					.map(renderItem)
					.join("");

				$groups.html(repeatedMarkup);
				groupWidth = $groups.first().outerWidth(true) || groupWidth;
			}

			const pixelsPerSecond = 110;
			const durationSeconds = Math.max(groupWidth / pixelsPerSecond, 8);

			$track.css("--ticker-distance", `${groupWidth}px`);
			$track.css("--ticker-duration", `${durationSeconds}s`);
		});
	}

	render_widgets() {
		Object.entries(this.widget_names).forEach(([key, widgetName]) => {
			if (key === "main_chart" || key === "mini_chart") {
				return;
			}

			if (key === "dividend_total") {
				this.mount_number_card(this.$dividendCard, widgetName);
				return;
			}

			const $slot = this.page.main.find(`[data-number-card="${key}"]`);
			if ($slot.length) {
				this.mount_number_card($slot, widgetName);
			}
		});
	}

	render_main_timeline() {
		const years = this.context.timeline_years || [];
		const flattenedValues = years.flatMap((year) => year.values || []);
		const maxValue = flattenedValues.length ? Math.max(...flattenedValues, 0) : 0;
		const chartScale = this.getChartScale(maxValue);
		const yTicks = this.buildTickValues(chartScale);

		this.$mainChart.html(`
			<div class="main-dashboard-timeline">
				<div class="main-dashboard-timeline-grid">
					${yTicks
						.map(
							(tick) => `
								<div class="main-dashboard-timeline-line" style="bottom:${tick.percent}%">
									<div class="main-dashboard-timeline-tick">${frappe.utils.escape_html(tick.label)}</div>
								</div>
							`
						)
						.join("")}
				</div>
				<div class="main-dashboard-timeline-years">
					${years
						.map((year) => this.render_timeline_year(year, chartScale.max))
						.join("")}
				</div>
			</div>
		`);
	}

	render_timeline_year(year, maxValue) {
		const months = [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		];

		return `
			<div class="main-dashboard-timeline-year">
				<div class="main-dashboard-timeline-months">
					${months
						.map((month, index) => {
							const value = Number((year.values || [])[index] || 0);
							const height = this.getBarHeightPercent(value, maxValue, { minPositivePercent: 1 });
							return `
								<div class="main-dashboard-timeline-month">
									<div class="main-dashboard-timeline-value">${frappe.utils.escape_html(this.formatCompactNumber(value))}</div>
									<div class="main-dashboard-timeline-bar-wrap">
										<div class="main-dashboard-timeline-bar" style="height:${height}%"></div>
									</div>
									<div class="main-dashboard-timeline-label">${frappe.utils.escape_html(month)}</div>
								</div>
							`;
						})
						.join("")}
				</div>
				<div class="main-dashboard-timeline-year-label">${frappe.utils.escape_html(String(year.year || ""))}</div>
			</div>
		`;
	}

	render_mini_timeline() {
		const years = this.context.mini_timeline_years || [];
		const monthLabels = [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		];
		const maxValue = years.length ? Math.max(...years.flatMap((year) => year.values || []), 0) : 0;
		const chartScale = this.getChartScale(maxValue);
		const palette = ["is-older", "is-middle", "is-latest"];

		this.$miniChart.html(`
			<div class="main-dashboard-mini-timeline">
				<div class="main-dashboard-mini-timeline-grid">
					${this.buildTickValues(chartScale)
						.map(
							(tick) => `
								<div class="main-dashboard-mini-timeline-line" style="bottom:${tick.percent}%">
									<div class="main-dashboard-mini-timeline-tick">${frappe.utils.escape_html(tick.label)}</div>
								</div>
							`
						)
						.join("")}
				</div>
				<div class="main-dashboard-mini-timeline-groups">
					${monthLabels
						.map((month, monthIndex) => {
							return `
								<div class="main-dashboard-mini-timeline-group">
									<div class="main-dashboard-mini-timeline-bars">
										${years
											.map((year, yearIndex) => {
												const value = Number((year.values || [])[monthIndex] || 0);
												const height = this.getBarHeightPercent(value, chartScale.max);
												const toneClass = palette[yearIndex] || "is-latest";
												return `
													<div class="main-dashboard-mini-timeline-bar-wrap">
														<div
															class="main-dashboard-mini-timeline-bar ${toneClass}"
															title="${frappe.utils.escape_html(String(year.year || ""))}: ${frappe.utils.escape_html(
																this.formatNumber(value)
															)}"
															style="height:${height}%"
														></div>
													</div>
												`;
											})
											.join("")}
									</div>
									<div class="main-dashboard-mini-timeline-label">${frappe.utils.escape_html(month)}</div>
								</div>
							`;
						})
						.join("")}
				</div>
			</div>
		`);
	}

	getChartScale(maxValue, tickCount = 3) {
		const safeMax = maxValue > 0 ? maxValue : 1;
		const roughStep = safeMax / tickCount;
		const magnitude = 10 ** Math.floor(Math.log10(roughStep || 1));
		const normalizedStep = roughStep / magnitude;
		const stepCandidates = [1, 2, 2.5, 5, 10];
		const roundedStep = stepCandidates.find((candidate) => normalizedStep <= candidate) || 10;
		const step = Math.max(roundedStep * magnitude, 1);
		const chartMax = Math.max(step * tickCount, safeMax);
		return { max: chartMax, step, tickCount };
	}

	buildTickValues(chartScale) {
		const { max, step, tickCount } = chartScale;
		return Array.from({ length: tickCount + 1 }, (_, index) => {
			const value = step * index;
			return {
				value,
				label: this.formatAxisNumber(value),
				percent: (value / max) * 100,
			};
		});
	}

	getBarHeightPercent(value, chartMax, options = {}) {
		const numericValue = Number(value || 0);
		const minPositivePercent = Number(options.minPositivePercent || 0);
		if (!chartMax || numericValue <= 0) {
			return 0;
		}

		const rawPercent = (numericValue / chartMax) * 100;
		return minPositivePercent ? Math.max(rawPercent, minPositivePercent) : rawPercent;
	}

	mount_chart($container, chartName, height) {
		$container.empty();
		frappe.widget.make_widget({
			widget_type: "chart",
			container: $container,
			label: chartName,
			chart_name: chartName,
			name: chartName,
			height: height,
			width: "Full",
		});
	}

	mount_number_card($container, cardName) {
		$container.empty();
		frappe.widget.make_widget({
			widget_type: "number_card",
			container: $container,
			label: cardName,
			number_card_name: cardName,
			name: cardName,
		});
	}

	formatNumber(value) {
		const numericValue = Number(value || 0);
		return numericValue.toLocaleString("en-US").replace(/,/g, " ");
	}

	formatCompactNumber(value) {
		const numericValue = Number(value || 0);
		if (!numericValue) {
			return "0";
		}
		if (Math.abs(numericValue) >= 1000) {
			const compact = numericValue / 1000;
			return `${Number.isInteger(compact) ? compact : compact.toFixed(1).replace(/\.0$/, "")}K`;
		}
		return this.formatNumber(numericValue);
	}

	formatAxisNumber(value) {
		const numericValue = Number(value || 0);
		if (!numericValue) {
			return "0K";
		}
		if (Math.abs(numericValue) >= 1000) {
			return `${Math.round(numericValue / 1000)}K`;
		}
		return `${Math.round(numericValue)}`;
	}
};
