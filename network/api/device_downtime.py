import frappe
from datetime import timezone
from frappe.utils import get_datetime, now, time_diff_in_seconds
import json

def _get_event_time(event_time, metrics=None):
    if not event_time and isinstance(metrics, dict):
        event_time = metrics.get("event_time")

    parsed_time = get_datetime(event_time) if event_time else get_datetime(now())

    if parsed_time.tzinfo:
        parsed_time = parsed_time.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed_time


def _parse_metrics(metrics):
    if isinstance(metrics, str):
        return json.loads(metrics)

    return metrics


@frappe.whitelist(methods=["POST"], allow_guest=False)
def start_downtime(device_id, issue_type, reason, metrics, event_time=None):
    try:
        metrics = _parse_metrics(metrics)

        open_logs = frappe.get_all("Device Downtime Log", filters={"device_id": device_id, "status": "Open"}, limit=1)
        if open_logs:
            return {"status": "ignored", "message": "Downtime already open"}

        doc = frappe.get_doc({
            "doctype": "Device Downtime Log",
            "device_id": device_id,
            "status": "Open",
            "issue_type": issue_type,
            "reason": reason,
            "start_time": _get_event_time(event_time, metrics),
            "metrics_snapshot": frappe.as_json(metrics) if isinstance(metrics, dict) else metrics
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "log_name": doc.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Downtime API - Start Failed")
        return {"status": "failed", "message": str(e)}


@frappe.whitelist(methods=["POST"], allow_guest=False)
def resolve_downtime(device_id, metrics=None, event_time=None):
    try:
        open_logs = frappe.get_all("Device Downtime Log", filters={"device_id": device_id, "status": "Open"})

        metrics = _parse_metrics(metrics)
        
        for log in open_logs:
            doc = frappe.get_doc("Device Downtime Log", log.name)
            doc.status = "Resolved"
            doc.end_time = _get_event_time(event_time, metrics)

            if metrics is not None:
                doc.resolution_metrics_snapshot = frappe.as_json(metrics)
            
            if doc.start_time:
                doc.duration = time_diff_in_seconds(doc.end_time, doc.start_time)
                
            doc.save(ignore_permissions=True)

        frappe.db.commit()
            
        return {"status": "success", "resolved_count": len(open_logs)}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Downtime API - Resolve Failed")
        return {"status": "failed", "message": str(e)}