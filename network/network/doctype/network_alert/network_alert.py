import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class NetworkAlert(Document):
    pass


@frappe.whitelist()
def acknowledge(name):

    alert = frappe.get_doc(
        "Network Alert",
        name
    )

    allowed_types = [
        "Device Down",
        "High Latency",
        "Packet Loss",
    ]

    if alert.alert_type not in allowed_types:
        frappe.throw(
            _("This alert type cannot be acknowledged.")
        )

    if alert.acknowledged:
        frappe.throw(
            _("This alert has already been acknowledged.")
        )

    if not alert.downtime:
        frappe.throw(
            _("This alert is not linked to a downtime incident.")
        )

    downtime = frappe.get_doc(
        "Network Downtime",
        alert.downtime
    )

    if downtime.status != "Open":
        frappe.throw(
            _("This incident has already been resolved.")
        )

    alert.acknowledged = 1
    alert.acknowledged_by = frappe.session.user
    alert.acknowledged_at = now_datetime()

    alert.save(ignore_permissions=True)

    return {
        "message": _("Alert acknowledged successfully.")
    }