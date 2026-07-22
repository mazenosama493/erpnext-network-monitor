import frappe
from frappe import _
from frappe.model.document import Document


class NetworkMonitorSettings(Document):

    def validate(self):
        self.validate_monitoring()
        self.validate_logging()
        self.validate_notifications()

    # --------------------------------------------------
    # Monitoring
    # --------------------------------------------------

    def validate_monitoring(self):

        if self.monitoring_interval_seconds <= 0:
            frappe.throw(
                _("Monitoring Interval must be greater than 0.")
            )

        if self.ping_timeout <= 0:
            frappe.throw(
                _("Ping Timeout must be greater than 0.")
            )

        if self.max_workers <= 0:
            frappe.throw(
                _("Max Workers must be greater than 0.")
            )

        if self.retry_count < 0:
            frappe.throw(
                _("Retry Count cannot be negative.")
            )

        if self.retry_delay < 0:
            frappe.throw(
                _("Retry Delay cannot be negative.")
            )

        if self.packets_per_check <= 0:
            frappe.throw(
                _("Packets Per Check must be greater than 0.")
            )

        if self.queue_batch_size <= 0:
            frappe.throw(
                _("Queue Batch Size must be greater than 0.")
            )

    # --------------------------------------------------
    # Logging
    # --------------------------------------------------

    def validate_logging(self):

        if self.keep_logs_days <= 0:
            frappe.throw(
                _("Keep Logs (Days) must be greater than 0.")
            )

    # --------------------------------------------------
    # Notifications
    # --------------------------------------------------

    def validate_notifications(self):

        if self.offline_alert_delay < 0:
            frappe.throw(
                _("Offline Alert Delay cannot be negative.")
            )

        if not self.enable_notifications:
            return

        if not self.notification_recipients:
            frappe.throw(
                _("Please add at least one notification recipient.")
            )

        users = set()

        for row in self.notification_recipients:

            if not row.recipient:
                frappe.throw(
                    _("Notification recipient cannot be empty.")
                )

            if row.recipient in users:
                frappe.throw(
                    _("Notification recipient '{0}' is duplicated.").format(
                        row.recipient
                    )
                )

            users.add(row.recipient)