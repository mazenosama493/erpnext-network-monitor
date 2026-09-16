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

    # If event_time was not passed directly, get it from metrics.
    if not event_time and isinstance(metrics, dict):
        event_time = metrics.get("event_time")

    # No event_time supplied -> use current Frappe time.
    if not event_time:
        return get_datetime(now())

    parsed_time = get_datetime(event_time)

    # Agent sends UTC timestamps.
    # Convert UTC to Egypt local time before storing
    # in MySQL DATETIME.
    if parsed_time.tzinfo:
        egypt_timezone = ZoneInfo("Africa/Cairo")
        parsed_time = parsed_time.astimezone(egypt_timezone)

        # MySQL DATETIME does not store timezone information.
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

        open_logs = frappe.get_all(
            "Device Downtime Log",
            filters={
                "device_id": device_id,
                "status": "Open",
            },
            limit=1,
        )

        if open_logs:
            return {
                "status": "ignored",
                "message": "Downtime already open",
            }

        start_time = _get_event_time(
            event_time,
            metrics,
        )

        doc = frappe.get_doc({
            "doctype": "Device Downtime Log",
            "device_id": device_id,
            "status": "Open",
            "issue_type": issue_type,
            "reason": reason,
            "start_time": start_time,
            "metrics_snapshot": (
                frappe.as_json(metrics)
                if isinstance(metrics, dict)
                else metrics
            ),
        })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "log_name": doc.name,
            "start_time": str(start_time),
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Downtime API - Start Failed",
        )

        return {
            "status": "failed",
            "message": str(e),
        }


@frappe.whitelist(methods=["POST"], allow_guest=False)
def resolve_downtime(
    device_id,
    metrics=None,
    event_time=None,
):
    try:
        open_logs = frappe.get_all(
            "Device Downtime Log",
            filters={
                "device_id": device_id,
                "status": "Open",
            },
        )

        metrics = _parse_metrics(metrics)

        end_time = _get_event_time(
            event_time,
            metrics,
        )

        for log in open_logs:
            doc = frappe.get_doc(
                "Device Downtime Log",
                log.name,
            )

            doc.status = "Resolved"
            doc.end_time = end_time

            if metrics is not None:
                doc.resolution_metrics_snapshot = frappe.as_json(
                    metrics
                )

            if doc.start_time and doc.end_time:
                total_seconds = time_diff_in_seconds(
                    doc.end_time,
                    doc.start_time,
                )

                # Frappe Duration fields expect the duration
                # to be stored as a number of seconds.
                doc.duration = total_seconds

            doc.save(ignore_permissions=True)

        frappe.db.commit()

        return {
            "status": "success",
            "resolved_count": len(open_logs),
        }

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Downtime API - Resolve Failed",
        )

        return {
            "status": "failed",
            "message": str(e),
        }
