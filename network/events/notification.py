import frappe

def after_notification_insert(doc, method):
    if not doc.for_user:
        return

    frappe.publish_realtime(
        event="notification",
        user=doc.for_user,
        after_commit=True  
    )