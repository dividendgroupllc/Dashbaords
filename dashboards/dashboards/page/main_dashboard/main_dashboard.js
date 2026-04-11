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
								<div class="main-dashboard-dividend-label">${__("Дивидент")}</div>
								<div class="main-dashboard-dividend-update-label">${__("Последнее обновление")}</div>
								<div class="main-dashboard-dividend-update-time" data-region="updated-at"></div>
							</div>
						</div>
					</div>
					<div class="main-dashboard-footer" data-region="footer-ticker"></div>
				</div>
			</div>
		`);

		this.$tabs = this.page.main.find('[data-region="tabs"]');
		this.$mainChart = this.page.main.find('[data-region="main-chart"]');
		this.$miniChart = this.page.main.find('[data-region="mini-chart"]');
		this.$summaryTable = this.page.main.find('[data-region="summary-table"]');
		this.$sideMetrics = this.page.main.find('[data-region="side-metrics"]');
		this.$dividendCard = this.page.main.find('[data-region="dividend-card"]');
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
		this.render_summary_table();
		this.render_side_metrics();
		this.render_footer();
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
		this.$footerTicker.html(
			items
				.map(
					(item) => `
						<div class="main-dashboard-footer-item">
							<span class="main-dashboard-footer-label">${frappe.utils.escape_html(item.label)}</span>
							<span class="main-dashboard-footer-value">${frappe.utils.escape_html(item.value)}</span>
						</div>
					`
				)
				.join("")
		);
	}

	render_widgets() {
		this.mount_chart(this.$mainChart, this.widget_names.main_chart, 314);
		this.mount_chart(this.$miniChart, this.widget_names.mini_chart, 126);

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
};
