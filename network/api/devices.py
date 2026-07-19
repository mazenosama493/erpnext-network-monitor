import frappe


@frappe.whitelist()
def get_devices():
    devices = frappe.get_all(
        "Network Device",
        filters={"enabled": 1},
        fields=[
            "name",
            "device_name",
            "host_name",
            "ip_address",
            "device_type",
            "site",
            "override_global_settings",
            "packets_per_check", 
            "monitoring_interval",
            "ping_timeout",
            "retry_count",
            "retry_delay",
            "critical_device",
            "notification_enabled",
        ],
        order_by="device_name asc",
    )

    return devices