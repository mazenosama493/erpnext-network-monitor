import re

import frappe
from frappe import _
from frappe.model.document import Document


class NetworkTag(Document):

    def validate(self):
        self.validate_tag_name()
        self.validate_tag_code()

    # ------------------------------------------------------------------
    # Tag Name
    # ------------------------------------------------------------------

    def validate_tag_name(self):
        self.tag_name = (self.tag_name or "").strip()

        if not self.tag_name:
            frappe.throw(_("Tag Name is required."))

    # ------------------------------------------------------------------
    # Tag Code
    # ------------------------------------------------------------------

    def validate_tag_code(self):
        self.tag_code = (self.tag_code or "").strip().upper()

        if not self.tag_code:
            frappe.throw(_("Tag Code is required."))

        if not re.fullmatch(r"[A-Z0-9_-]+", self.tag_code):
            frappe.throw(
                _(
                    "Tag Code may contain only uppercase letters, numbers, hyphens (-), and underscores (_)."
                )
            )