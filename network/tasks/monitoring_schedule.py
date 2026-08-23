import frappe
from frappe.utils import now_datetime, today, getdate

from network.api.downtime import close_open_downtimes
from network.api.unknown import set_status_unknown


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


    # =======================================
    # HOLIDAYS
    # =======================================    
    current_date = today()
    day_name = getdate(current_date).strftime("%A")
    is_holiday = False


    weekly_off_days = [row.day for row in settings.get("weekly_off_days", [])]
    if day_name in weekly_off_days:
        is_holiday = True
        frappe.log_error(title="Monitoring Schedule", message=f"Today is a weekly off: {day_name}")
    # =======================================
    # HOLIDAYS
    # =======================================

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
    
    if is_holiday:
        should_monitor = False
    else:
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
            f"Is Holiday: {is_holiday}\n"  # ضفناها في الـ Debug
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
        set_status_unknown(reason="Monitoring")  

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