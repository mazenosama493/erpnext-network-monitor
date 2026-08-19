import frappe


def set_status_unkown():
    devices=frappe.get_all(
        "Network Device",
        filters={
            "status": ["!=", "Unknown"],
        },
    )
    for device in devices:
        doc = frappe.get_doc("Network Device", device.name)
        doc.status = "Unknown"
        doc.save(ignore_permissions=True)