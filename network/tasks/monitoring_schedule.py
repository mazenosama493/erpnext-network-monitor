import frappe
from frappe.utils import now_datetime, today, getdate

from network.api.downtime import close_open_downtimes
from network.api.unknown import set_status_unknown

def check_monitoring_schedule():
    # ---------------------------------------
    # Debug: Start of the script
    # ---------------------------------------
    frappe.log_error(title="Monitoring Debug - Schedule", message="1. TASK STARTED: Evaluating Schedule")

    settings = frappe.get_single("Network Monitor Settings")

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
        frappe.log_error(title="Monitoring Debug - Schedule", message=f"Holiday detected: Today is {day_name}")
    # =======================================
    # HOLIDAYS
    # =======================================

    start_time = settings.monitoring_start_time
    stop_time = settings.monitoring_stop_time

    if not start_time or not stop_time:
        return

    current_time = now_datetime().time()
    current_minutes = (current_time.hour * 60) + current_time.minute

    start_hour, start_minute, _ = map(int, str(start_time).split(":"))
    stop_hour, stop_minute, _ = map(int, str(stop_time).split(":"))

    start_minutes = (start_hour * 60) + start_minute
    stop_minutes = (stop_hour * 60) + stop_minute

    if is_holiday:
        should_monitor = False
    else:
        if start_minutes < stop_minutes:
            should_monitor = (start_minutes <= current_minutes < stop_minutes)
        else:
            should_monitor = (current_minutes >= start_minutes or current_minutes < stop_minutes)

    new_enabled = 1 if should_monitor else 0

    frappe.log_error(
        title="Monitoring Debug - Schedule",
        message=(
            f"2. Schedule Evaluated:\n"
            f"Current Enabled in DB: {settings.enabled}\n"
            f"Calculated New Enabled: {new_enabled}"
        ),
    )

    # ---------------------------------------
    # Nothing changed (State is already correct)
    # ---------------------------------------
    if settings.enabled == new_enabled:
        if new_enabled == 0:
            open_downtimes = frappe.db.count("Network Downtime", {"status": "Open"})
            if open_downtimes > 0:
                frappe.log_error(title="Monitoring Debug - Schedule", message=f"3. Found {open_downtimes} lingering open downtimes while monitoring is OFF. Forcing cleanup.")
                
                close_open_downtimes(monitoring_down=True)
                frappe.db.commit()
                
                set_status_unknown(reason="Monitoring")
                frappe.db.commit()
        return

    # ---------------------------------------
    # State is changing
    # ---------------------------------------
    if not new_enabled: # Monitoring is stopping
        try:
            frappe.log_error(title="Monitoring Debug - Schedule", message="3. Stopping Monitoring: Starting close_open_downtimes...")
            close_open_downtimes(monitoring_down=True)
            frappe.db.commit()
            
            frappe.log_error(title="Monitoring Debug - Schedule", message="4. close_open_downtimes finished. Starting set_status_unknown...")
            status_response = set_status_unknown(reason="Monitoring")
            
            if status_response and status_response.get("status") == "error":
                frappe.log_error(
                    title="Monitoring Debug - Schedule Error", 
                    message=f"ABORTED: Skipped disabling monitoring because set_status_unknown failed: {status_response.get('message')}"
                )
                return 
            
            frappe.log_error(title="Monitoring Debug - Schedule", message="5. Devices set to Unknown. Now disabling Monitoring in Settings.")
            frappe.db.set_value("Network Monitor Settings", "Network Monitor Settings", "enabled", 0)
            frappe.db.commit()
            frappe.log_error(title="Monitoring Debug - Schedule", message="6. SUCCESS: Monitoring is now OFF.")

        except Exception as e:
            frappe.log_error(title="Monitoring Debug - Schedule Exception", message=f"FAILED to stop monitoring:\n{frappe.get_traceback()}")
            return
            
    else:
        # Monitoring is starting
        frappe.log_error(title="Monitoring Debug - Schedule", message="3. Starting Monitoring: Enabling in Settings.")
        frappe.db.set_value("Network Monitor Settings", "Network Monitor Settings", "enabled", 1)
        frappe.db.commit()
        frappe.log_error(title="Monitoring Debug - Schedule", message="4. SUCCESS: Monitoring is now ON.")