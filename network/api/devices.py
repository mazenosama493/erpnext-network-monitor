import frappe


@frappe.whitelist()
def get_devices():

    devices = frappe.db.sql(
        """
        SELECT
            d.name,
            d.device_name,
            d.host_name,
            d.ip_address,
            d.device_type,
            d.site,
            d.external_device,
            d.override_global_settings,
            d.packets_per_check,
            d.monitoring_interval,
            d.ping_timeout,
            d.retry_count,
            d.retry_delay,
            d.critical_device,
            d.notification_enabled
        FROM `tabNetwork Device` d
        INNER JOIN `tabNetwork Device Type` dt
            ON dt.name = d.device_type
        INNER JOIN `tabNetwork Site` s
            ON s.name = d.site
        WHERE
            d.enabled = 1
            AND dt.enabled = 1
            AND s.enabled = 1
        ORDER BY d.device_name ASC
        """,
        as_dict=True,
    )

    return devices