frappe.pages["product-by-customer"].on_page_load = function (wrapper) {
	new dashboards.ui.ProductByCustomerPage(wrapper);
};

frappe.provide("dashboards.ui");

dashboards.ui.ProductByCustomerPage = class ProductByCustomerPage {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Product by Customer"),
			single_column: true,
		});
		this.selectedCustomer = null;
		this.handleResize = () => this.syncScrollHeight();

		this.make_layout();
		$(window).off("resize.product-by-customer", this.handleResize);
		$(window).on("resize.product-by-customer", this.handleResize);
		this.load_context();
	}

	make_layout() {
		this.wrapper.find(".layout-main-section-wrapper").addClass("product-by-customer-layout");
		this.wrapper.find(".page-head").addClass("product-by-customer-page-head");
		this.page.main.removeClass("frappe-card");

		this.page.main.html(`
			<div class="product-by-customer-screen">
				<div class="product-by-customer-panel">
					<div class="product-by-customer-customer-strip" data-region="customers"></div>
					<div class="product-by-customer-hero">
						<div>
							<div class="product-by-customer-kicker" data-region="subtitle"></div>
							<div class="product-by-customer-title" data-region="title"></div>
						</div>
						<div class="product-by-customer-meta" data-region="meta"></div>
					</div>
					<div class="product-by-customer-content" data-region="content"></div>
				</div>
			</div>
		`);

		dashboards.ui.setupDashboardSidebar({
			page: this.page,
			route: "product-by-customer",
		});

		this.$customers = this.page.main.find('[data-region="customers"]');
		this.$title = this.page.main.find('[data-region="title"]');
		this.$subtitle = this.page.main.find('[data-region="subtitle"]');
		this.$meta = this.page.main.find('[data-region="meta"]');
		this.$content = this.page.main.find('[data-region="content"]');
	}

	load_context(customer) {
		if (customer !== undefined) {
			this.selectedCustomer = customer;
		}

		frappe.call({
			method: "dashboards.dashboards.page.product_by_customer.product_by_customer.get_dashboard_context",
			args: {
				customer: this.selectedCustomer,
			},
			callback: (r) => {
				this.context = r.message || {};
				this.selectedCustomer = this.context.selected_customer || null;
				this.render();
			},
		});
	}

	render() {
		this.render_customer_selector();
		this.$title.text(this.context.title || __("Product by Customer"));
		this.$subtitle.text(this.context.subtitle || "");
		this.render_meta();
		this.render_months();
		this.syncScrollHeight();
	}

	render_customer_selector() {
		const customers = this.context.customers || [];

		if (!customers.length) {
			this.$customers.html(`
				<div class="product-by-customer-empty-strip">${__("No customers found")}</div>
			`);
			return;
		}

		this.$customers.html(
			[
				{
					value: "",
					label: __("All Customers"),
				},
				...customers,
			]
				.map(
					(customer) => `
						<button
							class="product-by-customer-pill ${String(customer.value || "") === String(this.selectedCustomer || "") ? "is-active" : ""}"
							data-customer="${frappe.utils.escape_html(customer.value)}"
							title="${frappe.utils.escape_html(customer.label)}"
						>
							${frappe.utils.escape_html(customer.label)}
						</button>
					`
				)
				.join("")
		);

		this.$customers.find(".product-by-customer-pill").on("click", (e) => {
			const customer = $(e.currentTarget).data("customer") || null;
			if (customer !== this.selectedCustomer) {
				this.load_context(customer);
			}
		});
	}

	render_meta() {
		const years = (this.context.years || []).join(", ");
		const reference = [this.context.reference_month, this.context.reference_year].filter(Boolean).join(" ");
		const customer = this.context.selected_customer_label || __("All Customers");

		this.$meta.html(`
			<div class="product-by-customer-meta-line">${__("Customer")}: ${frappe.utils.escape_html(customer)}</div>
			<div class="product-by-customer-meta-line">${__("Years")}: ${frappe.utils.escape_html(years || "-")}</div>
			<div class="product-by-customer-meta-line">${__("Period")}: ${frappe.utils.escape_html(reference || "-")}</div>
		`);
	}

	render_months() {
		const months = this.context.months || [];
		if (!months.length || !months.some((month) => (month.items || []).length)) {
			this.$content.html(`
				<div class="product-by-customer-empty">
					<div class="product-by-customer-empty-title">${__("No product data found")}</div>
					<div class="product-by-customer-empty-copy">${__("No comparison data is available for the current period.")}</div>
				</div>
			`);
			this.$content.css({
				height: "",
				"max-height": "",
			});
			return;
		}

		this.$content.html(`
			<div class="product-by-customer-scroll">
				${months.map((month) => this.render_month(month)).join("")}
			</div>
		`);
	}

	syncScrollHeight() {
		const $scroll = this.$content.find(".product-by-customer-scroll");
		if (!$scroll.length) {
			return;
		}

		window.requestAnimationFrame(() => {
			const contentRect = this.$content.get(0)?.getBoundingClientRect();
			if (!contentRect) {
				return;
			}

			const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
			const bottomGap = 16;
			const minHeight = 320;
			const availableHeight = Math.floor(viewportHeight - contentRect.top - bottomGap);
			const nextHeight = Math.max(availableHeight, minHeight);

			$scroll.css({
				height: `${nextHeight}px`,
				"max-height": `${nextHeight}px`,
			});
		});
	}

	render_month(month) {
		const years = month.years || [];
		const items = month.items || [];
		const maxValue = Number(month.max_value || 0);

		return `
			<section class="product-by-customer-month">
				<div class="product-by-customer-month-title">${frappe.utils.escape_html(month.month_label || "")}</div>
				<div class="product-by-customer-grid" style="--pbc-year-count:${Math.max(years.length, 1)};">
					<div class="product-by-customer-head product-by-customer-head--item">${__("Предметы")}</div>
					${years
						.map(
							(year) => `
								<div class="product-by-customer-head">
									${frappe.utils.escape_html(String(year))}
								</div>
							`
						)
						.join("")}
					${items
						.map(
							(item) => `
								<div class="product-by-customer-item">${frappe.utils.escape_html(item.label || "")}</div>
								${(item.values || [])
									.map((value) => this.render_metric_cell(value, maxValue))
									.join("")}
							`
						)
						.join("")}
				</div>
				${
					month.hidden_item_count
						? `<div class="product-by-customer-footnote">+${month.hidden_item_count} ${__("more items")}</div>`
						: ""
				}
			</section>
		`;
	}

	render_metric_cell(value, maxValue) {
		const numericValue = Number(value || 0);
		const width = maxValue > 0 && numericValue > 0 ? Math.max((numericValue / maxValue) * 100, 6) : 0;

		return `
			<div class="product-by-customer-metric" title="${this.format_full_number(numericValue)}">
				<div class="product-by-customer-bar-track">
					${width ? `<div class="product-by-customer-bar-fill" style="width:${Math.min(width, 100)}%"></div>` : ""}
				</div>
				<div class="product-by-customer-metric-value">${this.format_compact_number(numericValue)}</div>
			</div>
		`;
	}

	format_compact_number(value) {
		const numericValue = Number(value || 0);
		if (!numericValue) {
			return "";
		}

		const absValue = Math.abs(numericValue);
		if (absValue >= 1000000) {
			return `${(numericValue / 1000000).toFixed(1).replace(/\.0$/, "")}M`;
		}

		if (absValue >= 1000) {
			return `${(numericValue / 1000).toFixed(1).replace(/\.0$/, "")}K`;
		}

		return this.format_full_number(numericValue);
	}

	format_full_number(value) {
		return Number(value || 0).toLocaleString("en-US").replace(/,/g, " ");
	}
};
