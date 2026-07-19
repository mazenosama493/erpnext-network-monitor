import frappe
from frappe.model.document import Document


class NetworkDevice(Document):

    def autoname(self):

        code = frappe.db.get_value(
            "Network Device Type",
            self.device_type,
            "code"
        )

        if not code:
            frappe.throw(
                f"Device Type '{self.device_type}' has no Code."
            )

        self.name = frappe.model.naming.make_autoname(
            f"{code}-.#####"
        )