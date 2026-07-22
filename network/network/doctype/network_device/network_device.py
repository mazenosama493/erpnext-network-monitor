import ipaddress
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class NetworkDevice(Document):

    # --------------------------------------------------
    # Naming
    # --------------------------------------------------

    def autoname(self):

        code = frappe.db.get_value(
            "Network Device Type",
            self.device_type,
            "code"
        )

        if not code:
            frappe.throw(
                _("Device Type '{0}' has no Code.").format(
                    self.device_type
                )
            )

        self.name = make_autoname(
            f"{code}-.#####"
        )

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate(self):

        self.normalize_fields()

        self.validate_general()

        self.validate_host()

        self.validate_mac_address()

        self.validate_override()

    # --------------------------------------------------
    # Normalize
    # --------------------------------------------------

    def normalize_fields(self):

        self.device_name = (
            self.device_name or ""
        ).strip()

        self.ip_address = (
            self.ip_address or ""
        ).strip().lower()

        if self.host_name:
            self.host_name = (
                self.host_name.strip()
            )

        if self.mac_address:
            self.mac_address = (
                self.mac_address
                .replace("-", ":")
                .replace(" ", "")
                .upper()
            )

        if self.description:
            self.description = (
                self.description.strip()
            )

        if self.notes:
            self.notes = (
                self.notes.strip()
            )

    # --------------------------------------------------
    # General Validation
    # --------------------------------------------------

    def validate_general(self):

        if not self.device_name:
            frappe.throw(
                _("Device Name is required.")
            )

        if not self.device_type:
            frappe.throw(
                _("Device Type is required.")
            )

        if not self.site:
            frappe.throw(
                _("Site is required.")
            )

    # --------------------------------------------------
    # Host Validation
    # --------------------------------------------------

    def validate_host(self):

        if not self.ip_address:
            frappe.throw(
                _("Host is required.")
            )

        # -----------------------------
        # Valid IPv4
        # -----------------------------
        try:
            ipaddress.ip_address(
                self.ip_address
            )
            return

        except ValueError:
            pass

        # -----------------------------
        # Hostname / Domain
        # -----------------------------
        hostname_regex = (
            r"^(?=.{1,253}$)"
            r"(?!-)"
            r"(?:[A-Za-z0-9]"
            r"(?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?"
            r"\.)*"
            r"[A-Za-z0-9]"
            r"(?:[A-Za-z0-9-]{0,61}"
            r"[A-Za-z0-9])?$"
        )

        if not re.fullmatch(
            hostname_regex,
            self.ip_address
        ):
            frappe.throw(
                _(
                    "Host must be a valid IPv4 address, hostname, or domain name."
                )
            )

    # --------------------------------------------------
    # MAC Address Validation
    # --------------------------------------------------

    def validate_mac_address(self):

        if not self.mac_address:
            return

        mac_regex = (
            r"^([0-9A-F]{2}:){5}"
            r"[0-9A-F]{2}$"
        )

        if not re.fullmatch(
            mac_regex,
            self.mac_address
        ):
            frappe.throw(
                _(
                    "MAC Address must be in the format AA:BB:CC:DD:EE:FF."
                )
            )

    # --------------------------------------------------
    # Override Validation
    # --------------------------------------------------

    def validate_override(self):

        if not self.override_global_settings:
            return

        if self.monitoring_interval <= 0:
            frappe.throw(
                _(
                    "Monitoring Interval must be greater than 0."
                )
            )

        if self.ping_timeout <= 0:
            frappe.throw(
                _(
                    "Ping Timeout must be greater than 0."
                )
            )

        if self.retry_count < 0:
            frappe.throw(
                _(
                    "Retry Count cannot be negative."
                )
            )

        if self.retry_delay < 0:
            frappe.throw(
                _(
                    "Retry Delay cannot be negative."
                )
            )

        if self.packets_per_check <= 0:
            frappe.throw(
                _(
                    "Packets Per Check must be greater than 0."
                )
            )