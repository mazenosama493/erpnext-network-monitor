import frappe
import json
import redis

REDIS_HOST = "192.168.2.41"
REDIS_PORT = 6379
CHANNEL = "network_agent_updates"


def ensure_pc_exists(device_id):
    if frappe.db.exists("PCs", {"pc_id": device_id}):
        return

    frappe.get_doc({
        "doctype": "PCs",
        "pc_id": device_id,
    }).insert(
        ignore_permissions=True,
        ignore_if_duplicate=True,
    )
    frappe.db.commit()


@frappe.whitelist(allow_guest=False)
def sync():
    request_data = frappe.request.get_json(silent=True) or frappe.form_dict
    payload = request_data.get("data", request_data)

    if isinstance(payload, str):
        payload = json.loads(payload)

    device_id = payload.get("device_id")
    metrics = request_data.get("metrics", payload)

    if not device_id or not metrics:
        return {"status": "failed", "message": "Missing device_id or metrics"}

    if isinstance(metrics, str):
        metrics = json.loads(metrics)

    ensure_pc_exists(device_id)

    metrics_json = json.dumps(metrics)
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )
    redis_client.setex(f"agent_metrics:{device_id}", 60, metrics_json)
    redis_client.publish(
        CHANNEL,
        json.dumps({"device_id": device_id, "metrics": metrics}),
    )

    return {"status": "success"}


@frappe.whitelist(allow_guest=False)
def get_active_devices():

    devices_list = []

    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )

        keys = r.keys("agent_metrics:*")

        for key in keys:

            device_id = key.replace("agent_metrics:", "")
            metrics_raw = r.get(key)

            if not metrics_raw:
                continue

            ensure_pc_exists(device_id)

            try:
                metrics_data = (
                    json.loads(metrics_raw)
                    if isinstance(metrics_raw, str)
                    else metrics_raw
                )
            except Exception:
                metrics_data = metrics_raw

            devices_list.append({
                "device_id": device_id,
                "metrics": metrics_data
            })

    except Exception as e:

        frappe.log_error(
            f"Redis Connection Error: {str(e)}",
            "Network Dashboard"
        )

    return devices_list