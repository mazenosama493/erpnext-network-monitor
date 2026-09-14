import click
import frappe
from network.realtime.redis_listener import listen

@click.command("start-network-listener")
@click.option("--site", default=None, help="Frappe site to publish realtime events for")
def start_network_listener(site):
    """Start Redis Pub/Sub listener for network agent updates."""
    site = site or frappe.get_conf().get("default_site")
    if not site:
        raise click.ClickException("No site supplied. Use --site <site>")

    frappe.init(site=site)
    frappe.connect()
    try:
        listen()
    finally:
        frappe.destroy()

commands = [start_network_listener]