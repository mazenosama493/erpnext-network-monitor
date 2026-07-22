import re

import frappe
from frappe import _
from frappe.model.document import Document


class NetworkDeviceType(Document):

    def validate(self):
        self.normalize_fields()
        self.validate_general()
        self.validate_code()

    # --------------------------------------------------

    def normalize_fields(self):

        self.device_type_name = (
            self.device_type_name or ""
        ).strip()

        self.code = (
            self.code or ""
        ).strip().upper()

        if self.description:
            self.description = (
                self.description.strip()
            )

    # --------------------------------------------------

    def validate_general(self):

        if not self.device_type_name:
            frappe.throw(
                _("Device Type Name is required.")
            )

        if not self.code:
            frappe.throw(
                _("Code is required.")
            )

    # --------------------------------------------------

    def validate_code(self):

        if not re.fullmatch(
            r"^[A-Z0-9]{2,10}$",
            self.code
        ):
            frappe.throw(
                _(
                    "Code must contain only uppercase letters and numbers (2–10 characters)."
                )
            )