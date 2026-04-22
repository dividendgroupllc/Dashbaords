import frappe
import random
from datetime import date
from frappe.utils import getdate

from frappe.utils import add_days, getdate, get_last_day

def run():
    # Find a company
    companies = frappe.get_all("Company", fields=["name"])
    if not companies:
        print("No companies found!")
        return
    company = companies[0].name
    print(f"Using company: {company}")
    
    # Filter items that have item_group set to avoid validation errors
    items = frappe.get_all("Item", filters={"item_group": ("!=", "")}, fields=["name"])

    customers = frappe.get_all("Customer", fields=["name"])

    if not customers:
        print("No customers found!")
        return
    if not items:
        print("No items with item group found!")
        # Try to find any item if the filter is too strict
        items = frappe.get_all("Item", fields=["name"])
        if not items:
            print("No items found at all!")
            return

    print(f"Found {len(customers)} customers and {len(items)} items.")

    for i in range(20):
        customer = random.choice(customers).name
        # Use date object
        p_date = date(2026, 1, random.randint(1, 31))
        p_date_str = p_date.strftime("%Y-%m-%d")
        d_date_str = add_days(p_date_str, 30)
        
        doc = frappe.new_doc("Sales Invoice")
        doc.customer = customer
        doc.company = company
        doc.posting_date = p_date_str
        doc.due_date = d_date_str
        doc.docstatus = 0 # Draft
        
        num_items = random.randint(1, 3)
        selected_items = random.sample(items, min(num_items, len(items)))
        for item in selected_items:
            doc.append("items", {
                "item_code": item.name,
                "qty": random.randint(1, 10),
                "rate": random.randint(50, 500)
            })
        
        try:
            doc.set_missing_values()
            doc.calculate_taxes_and_totals()
            # Reinforce dates after calculations
            doc.posting_date = p_date_str
            doc.due_date = d_date_str
            doc.insert(ignore_permissions=True)
            print(f"Created draft Sales Invoice: {doc.name} for {customer} on {p_date_str}")
        except Exception as e:
            print(f"Failed to create invoice {i+1}: {str(e)}")

    frappe.db.commit()

if __name__ == "__main__":
    run()
