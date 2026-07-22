import frappe
from frappe.model.document import Document
from frappe.utils import validate_email_address


class NetworkSite(Document):

    def validate(self):
        self.validate_site_code()
        self.validate_email()
        self.validate_phone()
        self.validate_required_data()

    def validate_site_code(self):
        """
        Ensure site code is normalized and unique.
        """
        if self.site_code:
            self.site_code = self.site_code.strip().upper()

            existing = frappe.db.exists(
                "Network Site",
                {
                    "site_code": self.site_code,
                    "name": ["!=", self.name]
                }
            )

            if existing:
                frappe.throw(
                    f"Site Code '{self.site_code}' already exists"
                )

    def validate_email(self):
        """
        Validate contact email format.
        """
        if self.email:
            try:
                validate_email_address(self.email, throw=True)
            except Exception:
                frappe.throw(
                    "Please enter a valid email address"
                )

    def validate_phone(self):
        """
        Basic phone validation.
        """
        if self.phone:
            phone = self.phone.replace(" ", "").replace("-", "")

            if not phone.isdigit():
                frappe.throw(
                    "Phone number must contain digits only"
                )

            if len(phone) < 7:
                frappe.throw(
                    "Phone number is too short"
                )

    def validate_required_data(self):
        """
        Business rule:
        Enabled sites should have contact information.
        """
        if self.enabled:
            if not self.contact_person and not self.email and not self.phone:
                frappe.throw(
                    "Enabled site must have at least one contact method"
                )