import frappe
from frappe.utils import add_days, now_datetime


def delete_old_checks():
    settings = frappe.get_single("Network Monitor Settings")

    retention_days = settings.check_retention_days or 30

    cutoff_date = add_days(
        now_datetime(),
        -retention_days
    )

    total_deleted = 0
    batch_size = 5000

    while True:
        names = frappe.get_all(
            "Network Check",
            filters={
                "creation": ["<", cutoff_date]
            },
            fields=["name"],
            limit=batch_size,
        )

        if not names:
            break

        names = [row.name for row in names]

        frappe.db.delete(
            "Network Check",
            {
                "name": ["in", names]
            }
        )

        frappe.db.commit()

        total_deleted += len(names)

        if len(names) < batch_size:
            break

    frappe.logger().info(
        f"Network Check cleanup deleted {total_deleted} records."
    )