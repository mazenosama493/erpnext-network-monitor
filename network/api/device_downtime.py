import frappe
from datetime import timezone
from frappe.utils import (
    get_datetime,
    now,
    time_diff_in_seconds,
)
import json
from zoneinfo import ZoneInfo


def _get_event_time(event_time, metrics=None):
    if not event_time and isinstance(metrics, dict):
        event_time = metrics.get("event_time")

    if not event_time:
        return get_datetime(now())

    parsed_time = get_datetime(event_time)

    if parsed_time.tzinfo:
        egypt_timezone = ZoneInfo("Africa/Cairo")
        parsed_time = parsed_time.astimezone(egypt_timezone)
        parsed_time = parsed_time.replace(tzinfo=None)

    return parsed_time


def _parse_metrics(metrics):
    if isinstance(metrics, str):
        return json.loads(metrics)
    return metrics


@frappe.whitelist(methods=["POST"], allow_guest=False)
def start_downtime(
    device_id,
    issue_type,
    reason,
    metrics,
    event_time=None,
):
    try:
        metrics = _parse_metrics(metrics)
        start_time = _get_event_time(event_time, metrics)

        open_logs = frappe.get_all(
            "Device Downtime Log",
            filters={"device_id": device_id, "status": "Open"},
            limit=1,
        )

        if open_logs:
            return update_downtime(device_id, issue_type, reason, metrics, event_time)

        # استخدام timeline_events المتطابق مع ملف الـ JSON الخاص بك
        doc = frappe.get_doc({
            "doctype": "Device Downtime Log",
            "device_id": device_id,
            "status": "Open",
            "start_time": start_time,
            "metrics_snapshot": frappe.as_json(metrics) if isinstance(metrics, dict) else metrics,
            "timeline_events": [
                {
                    "issue_type": issue_type,
                    "reason": reason,
                    "event_start": start_time
                }
            ]
        })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "log_name": doc.name,
            "start_time": str(start_time),
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Downtime API - Start Failed")
        return {"status": "failed", "message": str(e)}


@frappe.whitelist(methods=["POST"], allow_guest=False)
def update_downtime(
    device_id,
    issue_type,
    reason,
    metrics=None,
    event_time=None,
):
    try:
        metrics = _parse_metrics(metrics)
        current_time = _get_event_time(event_time, metrics)

        open_logs = frappe.get_all(
            "Device Downtime Log",
            filters={"device_id": device_id, "status": "Open"},
            limit=1,
        )

        if not open_logs:
            return start_downtime(device_id, issue_type, reason, metrics, event_time)

        doc = frappe.get_doc("Device Downtime Log", open_logs[0].name)
        
        # البحث في timeline_events عن آخر حدث مفتوح (الذي ملوش event_end)
        active_event = None
        for ev in doc.timeline_events:
            if not ev.event_end:
                active_event = ev
                break

        if active_event and active_event.issue_type == issue_type and active_event.reason == reason:
            return {"status": "ignored", "message": "Event unchanged"}

        if active_event:
            active_event.event_end = current_time

        doc.append("timeline_events", {
            "issue_type": issue_type,
            "reason": reason,
            "event_start": current_time
        })

        if metrics:
            doc.metrics_snapshot = frappe.as_json(metrics)

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": f"Timeline updated with new event: {issue_type}",
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Downtime API - Update Failed")
        return {"status": "failed", "message": str(e)}


@frappe.whitelist(methods=["POST"], allow_guest=False)
def resolve_downtime(
    device_id,
    metrics=None,
    event_time=None,
):
    try:
        open_logs = frappe.get_all(
            "Device Downtime Log",
            filters={"device_id": device_id, "status": "Open"},
        )

        metrics = _parse_metrics(metrics)
        end_time = _get_event_time(event_time, metrics)
        resolved_count = 0

        for log in open_logs:
            doc = frappe.get_doc("Device Downtime Log", log.name)
            
            # إغلاق أي حدث مفتوح في timeline_events
            for ev in doc.timeline_events:
                if not ev.event_end:
                    ev.event_end = end_time

            total_seconds = None
            if doc.start_time:
                total_seconds = int(time_diff_in_seconds(end_time, doc.start_time))
                if total_seconds < 0:
                    total_seconds = 0

            doc.status = "Resolved"
            doc.end_time = end_time
            doc.duration = total_seconds

            if metrics is not None:
                doc.resolution_metrics_snapshot = frappe.as_json(metrics)

            doc.save(ignore_permissions=True)
            resolved_count += 1

        frappe.db.commit()
        return {
            "status": "success",
            "resolved_count": resolved_count,
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Downtime API - Resolve Failed",
        )
        return {"status": "failed", "message": str(e)}