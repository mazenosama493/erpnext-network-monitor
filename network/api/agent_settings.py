import frappe

@frappe.whitelist(allow_guest=False)
def get_agent_settings():
    try:
        settings = frappe.get_doc("Network Agent Settings")
        
        return settings.as_dict()
        
    except Exception as e:
        frappe.log_error(f"Error fetching agent settings: {str(e)}", "Agent API")
        return {"error": str(e)}