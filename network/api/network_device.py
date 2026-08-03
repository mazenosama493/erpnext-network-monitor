import frappe


@frappe.whitelist()
def disable_devices(devices):
        if isinstance(devices, str):
            devices = frappe.parse_json(devices)

        for name in devices:
            doc = frappe.get_doc("Network Device", name)

            if doc.enabled:
                doc.enabled = 0
                doc.save(ignore_permissions=True)

        return {
            "message": f"{len(devices)} devices disabled."
        }