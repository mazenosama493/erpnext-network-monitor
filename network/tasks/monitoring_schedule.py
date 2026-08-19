import frappe
from frappe.utils import now_datetime

from network.api.downtime import close_open_downtimes
from network.api.unkown import set_status_unkown


def check_monitoring_schedule():

    # ---------------------------------------
    # Debug: prove scheduled task is running
    # ---------------------------------------
    frappe.log_error(
        title="Monitoring Schedule",
        message="TASK STARTED",
    )

    settings = frappe.get_single(
        "Network Monitor Settings"
    )

    # ---------------------------------------
    # Scheduled Monitoring Enabled?
    # ---------------------------------------
    if not settings.enable_scheduled_monitoring:
        return

    start_time = settings.monitoring_start_time
    stop_time = settings.monitoring_stop_time

    if not start_time or not stop_time:
        return

    # ---------------------------------------
    # Current Time
    # ---------------------------------------
    current_time = now_datetime().time()

    current_minutes = (
        current_time.hour * 60
        + current_time.minute
    )

    # ---------------------------------------
    # Frappe Time fields are strings
    # Example: "08:00:00"
    # ---------------------------------------
    start_hour, start_minute, _ = map(
        int,
        start_time.split(":")
    )

    stop_hour, stop_minute, _ = map(
        int,
        stop_time.split(":")
    )

    start_minutes = (
        start_hour * 60
        + start_minute
    )

    stop_minutes = (
        stop_hour * 60
        + stop_minute
    )

    # ---------------------------------------
    # Determine monitoring state
    # ---------------------------------------

    # Normal schedule
    # Example: 08:00 -> 22:00
    if start_minutes < stop_minutes:

        should_monitor = (
            start_minutes
            <= current_minutes
            < stop_minutes
        )

    # Overnight schedule
    # Example: 22:00 -> 08:00
    else:

        should_monitor = (
            current_minutes >= start_minutes
            or current_minutes < stop_minutes
        )

    new_enabled = 1 if should_monitor else 0

    # ---------------------------------------
    # Debug
    # ---------------------------------------
    frappe.log_error(
        title="Monitoring Schedule Debug",
        message=(
            f"Current Time: {current_time}\n"
            f"Start Time: {start_time}\n"
            f"Stop Time: {stop_time}\n"
            f"Current Enabled: {settings.enabled}\n"
            f"New Enabled: {new_enabled}"
        ),
    )

    # ---------------------------------------
    # Nothing changed
    # ---------------------------------------
    if settings.enabled == new_enabled:
        return

    # ---------------------------------------
    # Monitoring is being stopped
    # ---------------------------------------
    if not new_enabled:

        close_open_downtimes(
            device_disabled=False,
        )
        set_status_unkown()

    # ---------------------------------------
    # Update Monitoring Enabled
    # ---------------------------------------
    frappe.db.set_value(
        "Network Monitor Settings",
        None,
        "enabled",
        new_enabled,
    )

    frappe.db.commit()