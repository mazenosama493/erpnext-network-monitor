import frappe

from network.services.check_processor import CheckProcessor



@frappe.whitelist(methods=["POST"])
def submit_checks():

    data = frappe.form_dict

    if hasattr(data, "get"):
        checks = data.get("checks", [])
    else:
        checks = []

    processor = CheckProcessor()

    return processor.process(checks)