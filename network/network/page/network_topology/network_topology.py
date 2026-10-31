import os
import json
import base64
import hashlib
import mimetypes
import frappe


# --------------------------------------------------
# Cache helpers
# --------------------------------------------------

ICON_CACHE = "network_topology_icons"   # permanent, keyed by icon file URL
CACHE_PREFIX = "network_topology:"      # short TTL, cleared on every edit
CACHE_TTL = 10                          # seconds, map topology
PUBLIC_STATUS_TTL = 5                   # seconds, guest status polling


def _cache():
    """Work on both old (frappe.cache()) and new (frappe.cache) Frappe versions."""
    cache = frappe.cache
    return cache if hasattr(cache, "get_value") else cache()


def cached(key, builder, ttl=CACHE_TTL):
    data = _cache().get_value(key)
    if data is None:
        data = builder()
        _cache().set_value(key, data, expires_in_sec=ttl)
    return data


def clear_topology_cache():
    _cache().delete_keys(CACHE_PREFIX)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def get_public_node_id(device_name):
    return hashlib.sha256(device_name.encode("utf-8")).hexdigest()


def _read_icon_as_data_uri(file_url):
    """Convert a Frappe attached image (/files/... or /private/files/...) into a Base64 Data URI."""
    if not file_url:
        return None

    file_url = str(file_url).strip()
    if file_url.startswith("data:image/"):
        return file_url

    if file_url.startswith("/files/"):
        file_path = frappe.get_site_path("public", file_url.lstrip("/"))
    elif file_url.startswith("/private/files/"):
        file_path = frappe.get_site_path(file_url.lstrip("/"))
    else:
        return None

    if not os.path.exists(file_path):
        return None

    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "image/png"
        with open(file_path, "rb") as f:
            b64_data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{b64_data}"
    except Exception:
        return None


def get_topology_icon_data_uri(file_url):
    """Cached wrapper: reads and encodes each icon file once, not on every request.

    The key is the file URL. Frappe gives a re-uploaded file a new URL, so
    replacing a device type's icon is picked up automatically. If a file is ever
    overwritten in place, clear it with:
        frappe.cache().delete_value("network_topology_icons")
    """
    if not file_url:
        return None

    file_url = str(file_url).strip()
    if file_url.startswith("data:image/"):
        return file_url

    uri = _cache().hget(ICON_CACHE, file_url)
    if not uri:
        uri = _read_icon_as_data_uri(file_url)
        if uri:
            _cache().hset(ICON_CACHE, file_url, uri)
    return uri


# --------------------------------------------------
# Maps
# --------------------------------------------------

@frappe.whitelist()
def get_maps():
    maps = frappe.get_all(
        "Network Map",
        filters={"enabled": 1},
        fields=["name", "map_name", "is_default", "description"],
        order_by="is_default desc, creation asc"
    )
    if not maps:
        doc = frappe.get_doc({
            "doctype": "Network Map",
            "map_name": "Overall Network Diagram",
            "is_default": 1,
            "enabled": 1
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        maps = [{
            "name": doc.name,
            "map_name": doc.map_name,
            "is_default": 1,
            "description": ""
        }]
    return maps


def _build_map_topology(map_name):
    map_doc = frappe.get_doc("Network Map", map_name)

    all_devices = frappe.get_all(
        "Network Device",
        filters={"enabled": 1},
        fields=["name", "device_name", "ip_address", "device_type", "status", "response_time", "critical_device"]
    )
    device_lookup = {d.name: d for d in all_devices}

    device_types = {}
    for dt in frappe.get_all(
        "Network Device Type",
        fields=["name", "device_type_name", "code", "color", "icon", "topology_icon"]
    ):
        device_types[dt.name] = dt

    map_nodes = getattr(map_doc, "nodes", []) or []
    map_device_ids = [row.device for row in map_nodes if row.device in device_lookup]

    latest_checks = {}
    if map_device_ids:
        checks = frappe.db.sql("""
            SELECT nc.device, nc.packet_loss, nc.avg_response_time, nc.jitter
            FROM `tabNetwork Check` nc
            INNER JOIN (
                SELECT device, MAX(check_time) AS max_time
                FROM `tabNetwork Check`
                WHERE device IN %(devices)s
                GROUP BY device
            ) latest ON nc.device = latest.device AND nc.check_time = latest.max_time
        """, {"devices": map_device_ids}, as_dict=True)
        latest_checks = {c.device: c for c in checks}

    open_downtimes = {}
    if map_device_ids:
        downtimes = frappe.get_all(
            "Network Downtime",
            filters={"status": "Open", "device": ["in", map_device_ids]},
            fields=["device", "started_at", "duration_minutes", "reason"]
        )
        open_downtimes = {dt.device: dt for dt in downtimes}

    # One icon per device type used on this map, sent once instead of per node
    icons = {}

    nodes = []
    for row in map_nodes:
        dev = device_lookup.get(row.device)
        if not dev:
            continue

        chk = latest_checks.get(dev.name, {})
        dt_meta = device_types.get(dev.device_type, {})
        downtime = open_downtimes.get(dev.name)

        if dev.device_type not in icons:
            icons[dev.device_type] = get_topology_icon_data_uri(dt_meta.get("topology_icon")) or ""

        packet_loss = float(chk.get("packet_loss") or 0.0)
        resp_time = float(dev.response_time or chk.get("avg_response_time") or 0.0)

        visual_state = dev.status or "Unknown"
        if dev.status == "Online" and (packet_loss > 0 or resp_time > 200):
            visual_state = "Warning"

        nodes.append({
            "row_name": row.name,
            "id": dev.name,
            "label": dev.device_name,
            "ip_address": dev.ip_address,
            "device_type": dev.device_type,
            "type_code": dt_meta.get("code") or dev.device_type,
            "type_color": dt_meta.get("color") or "#3b82f6",
            "type_icon": dt_meta.get("icon") or "octicon octicon-cpu",
            "status": dev.status,
            "visual_state": visual_state,
            "response_time": round(resp_time, 2),
            "packet_loss": round(packet_loss, 1),
            "critical": dev.critical_device,
            "downtime_reason": downtime.reason if downtime else None,
            "downtime_started": str(downtime.started_at) if downtime else None,
            "x": float(row.map_x or 150),
            "y": float(row.map_y or 150)
        })

    valid_node_ids = {n["id"] for n in nodes}

    map_links = getattr(map_doc, "links", []) or []
    links = []
    for row in map_links:
        if row.source_device in valid_node_ids and row.target_device in valid_node_ids:
            links.append({
                "id": row.name,
                "source_device": row.source_device,
                "target_device": row.target_device,
                "connection_type": row.connection_type or "Cable",
                "source_port": row.source_port or "",
                "target_port": row.target_port or ""
            })

    available_devices = [
        {"name": d.name, "device_name": d.device_name, "ip_address": d.ip_address, "device_type": d.device_type}
        for d in all_devices if d.name not in valid_node_ids
    ]

    return {
        "map_name": map_doc.name,
        "nodes": nodes,
        "links": links,
        "available_devices": available_devices,
        "icons": icons,
    }


@frappe.whitelist()
def get_map_topology(map_name):
    return cached(f"{CACHE_PREFIX}{map_name}", lambda: _build_map_topology(map_name))


# --------------------------------------------------
# Public (guest) endpoints
# --------------------------------------------------

@frappe.whitelist(allow_guest=True)
def get_public_maps():
    return frappe.get_all(
        "Network Map",
        filters={"enabled": 1},
        fields=["name", "map_name", "is_default"],
        order_by="is_default desc, creation asc"
    )


@frappe.whitelist(allow_guest=True)
def get_public_map_topology(map_name):
    map_name_label = frappe.db.get_value(
        "Network Map",
        {"name": map_name, "enabled": 1},
        "map_name"
    )
    if not map_name_label:
        frappe.throw("Map not found.", frappe.DoesNotExistError)

    topology = get_map_topology(map_name)
    icons = topology.get("icons") or {}
    public_ids = {node["id"]: get_public_node_id(node["id"]) for node in topology["nodes"]}

    public_nodes = []
    for node in topology["nodes"]:
        visual_state = node["status"] or "Unknown"
        if visual_state == "Online" and (
            node["packet_loss"] > 0 or node["response_time"] > 150
        ):
            visual_state = "Warning"
        public_nodes.append({
            "id": public_ids[node["id"]],
            "label": node["label"],
            "device_type": node["device_type"],
            "type_icon": node["type_icon"],
            # keeps the public response shape unchanged for the public page JS
            "topology_icon": icons.get(node["device_type"], ""),
            "visual_state": visual_state,
            "x": node["x"],
            "y": node["y"],
        })

    return {
        "map_name": map_name_label,
        "nodes": public_nodes,
        "links": [
            {
                "id": f"link-{index}",
                "source_device": public_ids[link["source_device"]],
                "target_device": public_ids[link["target_device"]],
                "connection_type": link["connection_type"],
            }
            for index, link in enumerate(topology["links"])
        ],
    }


def _build_public_map_statuses(map_name):
    map_name = frappe.db.get_value(
        "Network Map",
        {"name": map_name, "enabled": 1},
        "name",
    )
    if not map_name:
        frappe.throw("Map not found.", frappe.DoesNotExistError)
    map_doc = frappe.get_doc("Network Map", map_name)
    device_names = [row.device for row in (map_doc.nodes or []) if row.device]
    if not device_names:
        return []

    devices = frappe.get_all(
        "Network Device",
        filters={"name": ["in", device_names], "enabled": 1},
        fields=["name", "status", "response_time"],
    )
    checks = frappe.db.sql(
        """
        SELECT nc.device, nc.packet_loss, nc.avg_response_time
        FROM `tabNetwork Check` nc
        INNER JOIN (
            SELECT device, MAX(check_time) AS max_time
            FROM `tabNetwork Check`
            WHERE device IN %(devices)s
            GROUP BY device
        ) latest ON nc.device = latest.device AND nc.check_time = latest.max_time
        """,
        {"devices": [device.name for device in devices]},
        as_dict=True,
    ) if devices else []
    latest_checks = {check.device: check for check in checks}

    statuses = []
    for device in devices:
        check = latest_checks.get(device.name, {})
        response_time = float(device.response_time or check.get("avg_response_time") or 0)
        packet_loss = float(check.get("packet_loss") or 0)
        visual_state = device.status or "Unknown"
        if visual_state == "Online" and (packet_loss > 0 or response_time > 150):
            visual_state = "Warning"

        statuses.append({
            "node_id": get_public_node_id(device.name),
            "status": visual_state,
            "response_time": response_time,
            "packet_loss": packet_loss,
        })

    return statuses


@frappe.whitelist(allow_guest=True)
def get_public_map_statuses(map_name):
    # Guest-accessible, so cache it: load no longer depends on how many people poll it
    return cached(
        f"{CACHE_PREFIX}public_status:{map_name}",
        lambda: _build_public_map_statuses(map_name),
        ttl=PUBLIC_STATUS_TTL,
    )


# --------------------------------------------------
# Map editing (every one of these clears the cache)
# --------------------------------------------------

@frappe.whitelist()
def save_map_positions(map_name, positions):
    if isinstance(positions, str):
        positions = json.loads(positions)

    pos_map = {p["id"]: p for p in positions}
    map_doc = frappe.get_doc("Network Map", map_name)
    map_nodes = getattr(map_doc, "nodes", []) or []

    for row in map_nodes:
        if row.device in pos_map:
            row.map_x = float(pos_map[row.device]["x"])
            row.map_y = float(pos_map[row.device]["y"])

    map_doc.save()
    clear_topology_cache()
    return {"status": "saved"}


@frappe.whitelist()
def add_device_to_map(map_name, device, map_x=250, map_y=200):
    map_doc = frappe.get_doc("Network Map", map_name)
    map_nodes = getattr(map_doc, "nodes", []) or []
    existing = {row.device for row in map_nodes}

    if device == "__ALL__":
        all_devs = frappe.get_all("Network Device", filters={"enabled": 1}, pluck="name")
        idx = len(existing)
        for d in all_devs:
            if d not in existing:
                map_doc.append("nodes", {
                    "device": d,
                    "map_x": 140 + (idx % 8) * 140,
                    "map_y": 120 + (idx // 8) * 130
                })
                idx += 1
    else:
        if device in existing:
            frappe.throw("This device is already on the map.")
        map_doc.append("nodes", {
            "device": device,
            "map_x": float(map_x),
            "map_y": float(map_y)
        })

    map_doc.save()
    clear_topology_cache()
    return {"status": "added"}


@frappe.whitelist()
def remove_device_from_map(map_name, device):
    map_doc = frappe.get_doc("Network Map", map_name)
    if hasattr(map_doc, "nodes"):
        map_doc.nodes = [r for r in map_doc.nodes if r.device != device]
    if hasattr(map_doc, "links"):
        map_doc.links = [
            r for r in map_doc.links
            if r.source_device != device and r.target_device != device
        ]
    map_doc.save()
    clear_topology_cache()
    return {"status": "removed"}


@frappe.whitelist()
def add_link_to_map(map_name, source_device, target_device, connection_type="Cable", source_port=None, target_port=None):
    if source_device == target_device:
        frappe.throw("Cannot link a device to itself.")

    existing = frappe.db.exists(
        "Network Map Link",
        {
            "parent": map_name,
            "parenttype": "Network Map",
            "parentfield": "links",
            "source_device": source_device,
            "target_device": target_device
        }
    )
    if existing:
        frappe.throw("A link between these devices already exists on this map.")

    child_row_name = frappe.generate_hash(length=10)
    max_idx = frappe.db.sql("""
        SELECT IFNULL(MAX(idx), 0) FROM `tabNetwork Map Link` 
        WHERE parent = %(parent)s AND parenttype = 'Network Map' AND parentfield = 'links'
    """, {"parent": map_name})[0][0]

    frappe.db.sql("""
        INSERT INTO `tabNetwork Map Link` 
        (name, parent, parenttype, parentfield, idx, source_device, target_device, connection_type, source_port, target_port, docstatus, creation, modified)
        VALUES 
        (%(name)s, %(parent)s, 'Network Map', 'links', %(idx)s, %(source)s, %(target)s, %(type)s, %(sp)s, %(tp)s, 0, NOW(), NOW())
    """, {
        "name": child_row_name,
        "parent": map_name,
        "idx": max_idx + 1,
        "source": source_device,
        "target": target_device,
        "type": connection_type,
        "sp": source_port,
        "tp": target_port
    })

    frappe.db.commit()
    clear_topology_cache()
    return {"status": "linked"}


@frappe.whitelist()
def remove_link_from_map(map_name, link_id):
    frappe.db.delete("Network Map Link", {"name": link_id, "parent": map_name})
    frappe.db.commit()
    clear_topology_cache()
    return {"status": "deleted"}


def broadcast_device_status_change(device_name, new_status, response_time, packet_loss):
    frappe.publish_realtime(
        event="network_device_status_update",
        message={
            "device": device_name,
            "status": new_status,
            "response_time": response_time,
            "packet_loss": packet_loss
        },
        after_commit=True
    )