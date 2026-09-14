import json
import redis
import frappe


REDIS_HOST = "127.0.0.1"
REDIS_PORT = 13000

CHANNEL = "network_agent_updates"


def listen():

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
    )

    pubsub = r.pubsub()

    pubsub.subscribe(CHANNEL)

    print(
        f"Network realtime listener started on {CHANNEL}"
    )

    for message in pubsub.listen():

        if message["type"] != "message":
            continue

        try:

            data = json.loads(message["data"])
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                data = data["data"]

            device_id = data.get("device_id")
            metrics = data.get("metrics")

            if not device_id or metrics is None:
                continue

            frappe.publish_realtime(
                event="live_network_update",
                message={
                    "device_id": device_id,
                    "metrics": metrics,
                },
                after_commit=False,
            )

        except Exception as e:

            frappe.log_error(
                f"Network realtime listener error: {str(e)}",
                "Network Realtime Listener",
            )