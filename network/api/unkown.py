import frappe


def set_status_unknown(reason, device_name=None):
    try:
        if reason == "Monitoring":
            devices = frappe.get_all(
                "Network Device",
                filters={
                    "status": ["!=", "Unknown"],
                },
                pluck="name",
            )

            for device_name in devices:
                doc = frappe.get_doc("Network Device", device_name)
                doc.status = "Unknown"
                doc.save(ignore_permissions=True)

        elif reason == "Device Disabled":
            if not device_name:
                frappe.throw("Device name is required when reason is 'Device Disabled'")

            device = frappe.get_doc("Network Device", device_name)
            device.status = "Unknown"
            device.save(ignore_permissions=True)

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Error in set_status_unknown"
        )
        return {
            "status": "error",
            "message": str(e),
        }