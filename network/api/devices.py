import frappe


@frappe.whitelist()
def get_devices():

    devices = frappe.db.sql(
        """
        SELECT
            name,
            device_name,
            host_name,
            ip_address,
            device_type,
            site,
            external_device,
            override_global_settings,
            packets_per_check,
            monitoring_interval,
            ping_timeout,
            retry_count,
            retry_delay,
            critical_device,
            notification_enabled
        FROM `tabNetwork Device`
        WHERE enabled = 1
        ORDER BY device_name ASC
        """,
        as_dict=True,
    )

    return devices