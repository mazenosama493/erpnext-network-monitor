import frappe
from frappe.utils import time_diff_in_seconds


class CheckProcessor:

    def process(self, checks):

        processed = 0
        failed = 0

        for check in checks:
            try:
                self.process_check(check)
                processed += 1

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    "Network Check Processor"
                )
                failed += 1

        return {
            "processed": processed,
            "failed": failed
        }


    # --------------------------------------------------
    # Main Processing
    # --------------------------------------------------

    def process_check(self, check):

        self.validate_check(check)

        device = self.get_device(
            check["device"]
        )

        old_status = device.status
        new_status = check["status"]


        # Save check history
        self.create_network_check(
            device,
            check
        )


        # --------------------------------------------------
        # Handle device state
        # --------------------------------------------------

        if new_status == "Offline":

            # Every offline check counts
            self.handle_device_down(
                device,
                check
            )


        elif (
            old_status == "Offline"
            and new_status == "Online"
        ):

            # Recovery only
            self.handle_device_recovered(
                device,
                check
            )


        # Update current device state
        self.update_device(
            device,
            check
        )


    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate_check(self, check):

        required = [
            "device",
            "status",
            "avg_response_time",
            "check_time",
        ]

        for field in required:

            if field not in check:
                raise Exception(
                    f"Missing field: {field}"
                )


    # --------------------------------------------------
    # Device
    # --------------------------------------------------

    def get_device(self, device_name):

        return frappe.get_doc(
            "Network Device",
            device_name
        )


    def update_device(self, device, check):

        device.status = check["status"]

        device.last_check = check["check_time"]

        device.response_time = check.get(
            "avg_response_time"
        )


        if check["status"] == "Online":

            device.last_seen = check["check_time"]


        device.save(
            ignore_permissions=True
        )


    # --------------------------------------------------
    # Network Check
    # --------------------------------------------------

    def create_network_check(self, device, check):

        doc = frappe.new_doc(
            "Network Check"
        )

        doc.device = device.name

        doc.device_type = device.device_type

        doc.check_time = check.get(
            "check_time"
        )

        doc.status = check.get(
            "status"
        )

        doc.avg_response_time = check.get(
            "avg_response_time"
        )

        doc.min_response_time = check.get(
            "min_response_time"
        )

        doc.max_response_time = check.get(
            "max_response_time"
        )

        doc.jitter = check.get(
            "jitter"
        )

        doc.packet_loss = check.get(
            "packet_loss",
            0
        )

        doc.packets_sent = check.get(
            "packets_sent",
            0
        )

        doc.packets_received = check.get(
            "packets_received",
            0
        )

        doc.error_message = check.get(
            "error_message"
        )

        doc.worker = check.get(
            "worker"
        )

        doc.execution_time = check.get(
            "execution_time"
        )


        doc.insert(
            ignore_permissions=True
        )


    # --------------------------------------------------
    # Device Down
    # --------------------------------------------------

    def handle_device_down(self, device, check):

        downtime = frappe.db.exists(
            "Network Downtime",
            {
                "device": device.name,
                "status": "Open"
            }
        )


        if downtime:

            # already down
            self.increment_downtime_checks(
                downtime
            )


        else:

            # first failure
            self.create_downtime(
                device,
                check
            )

            self.create_alert(
                device,
                check
            )


    # --------------------------------------------------
    # Device Recovery
    # --------------------------------------------------

    def handle_device_recovered(self, device, check):

        downtime = frappe.db.exists(
            "Network Downtime",
            {
                "device": device.name,
                "status": "Open"
            }
        )


        if downtime:

            self.close_downtime(
                device,
                check
            )

            self.create_recovery_alert(
                device,
                check
            )


    # --------------------------------------------------
    # Downtime
    # --------------------------------------------------

    def create_downtime(self, device, check):

        doc = frappe.new_doc(
            "Network Downtime"
        )


        doc.device = device.name

        doc.started_at = check["check_time"]

        doc.status = "Open"

        doc.number_of_checks = 1


        doc.average_response_before_failure = (
            device.response_time
        )


        doc.insert(
            ignore_permissions=True
        )


        return doc.name



    def increment_downtime_checks(self, downtime_name):

        downtime = frappe.get_doc(
            "Network Downtime",
            downtime_name
        )


        downtime.number_of_checks = (
            downtime.number_of_checks or 0
        ) + 1


        downtime.save(
            ignore_permissions=True
        )



    def close_downtime(self, device, check):

        name = frappe.db.get_value(
            "Network Downtime",
            {
                "device": device.name,
                "status": "Open"
            },
            "name"
        )


        if not name:
            return


        downtime = frappe.get_doc(
            "Network Downtime",
            name
        )


        downtime.ended_at = check["check_time"]


        seconds = time_diff_in_seconds(
            downtime.ended_at,
            downtime.started_at
        )


        downtime.duration_minutes = round(
            seconds / 60,
            2
        )


        downtime.status = "Closed"


        downtime.save(
            ignore_permissions=True
        )


    # --------------------------------------------------
    # Alerts
    # --------------------------------------------------

    def create_alert(self, device, check):

        alert = frappe.new_doc(
            "Network Alert"
        )


        alert.device = device.name

        alert.device_type = device.device_type

        alert.alert_time = check["check_time"]

        alert.alert_type = "Device Down"


        if device.critical_device:

            alert.severity = "Critical"

        else:

            alert.severity = "Warning"


        alert.insert(
            ignore_permissions=True
        )



    def create_recovery_alert(self, device, check):

        alert = frappe.new_doc(
            "Network Alert"
        )


        alert.device = device.name

        alert.device_type = device.device_type

        alert.alert_time = check["check_time"]

        alert.alert_type = "Device Recovered"

        alert.severity = "Info"


        alert.insert(
            ignore_permissions=True
        )