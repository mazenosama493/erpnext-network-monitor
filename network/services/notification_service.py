import frappe
from frappe.utils import now
from frappe.desk.doctype.notification_log.notification_log import (
    enqueue_create_notification,
)
from frappe.utils.data import format_datetime


class NotificationService:

    def send(self, alert):

        # ---------------------------------------
        # Global Notifications Enabled?
        # ---------------------------------------
        settings = frappe.get_single(
            "Network Monitor Settings"
        )

        if not settings.enable_notifications:
            return

        # ---------------------------------------
        # Device Notifications Enabled?
        # ---------------------------------------
        device = frappe.get_doc(
            "Network Device",
            alert.device
        )

        if not device.notification_enabled:
            return

        # ---------------------------------------
        # Send Notification
        # ---------------------------------------
        self.send_system_notification(
            alert,
            device
        )

        # ---------------------------------------
        # Update Alert
        # ---------------------------------------
        alert.notification_sent = 1
        alert.notification_time = now()
        alert.notification_method = "System Notification"

        alert.save(
            ignore_permissions=True
        )

    def send_system_notification(self, alert, device):


        settings = frappe.get_single(
            "Network Monitor Settings"
        )

        users = [
            row.recipient
            for row in settings.notification_recipients
            if row.enabled and row.recipient
        ]

        if not users:
            return
        
        frappe.log_error(
                title="Notification Debug Users",
                message=str(users)
            )

        enqueue_create_notification(
            users=users,
            doc={
                "type": "Alert",
                "document_type": "Network Alert",
                "document_name": alert.name,
                "subject": (
                    f"{device.device_name} - {alert.alert_type} "
                    f"({format_datetime(alert.alert_time)})"
                ),
                "email_content": (
                    f"{device.device_name} is {alert.alert_type}"
                ),
                "from_user": "Administrator",
                "creation": alert.alert_time,
            },
        )