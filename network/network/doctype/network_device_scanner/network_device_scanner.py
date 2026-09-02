
import frappe
from frappe.model.document import Document
import requests


class NetworkDeviceScanner(Document):

    @frappe.whitelist()
    def fetch_device_info(self):
        if not self.ip:
            frappe.throw("Please enter the IP first.")

        # Get API URL from Network Device Scanner Settings
        settings = frappe.get_single("Network Device Scanner Settings")
        api_url = settings.api_url



        if not api_url.startswith(("http://", "https://")):
            api_url = f"http://{api_url}"

        if not api_url:
            frappe.throw(
                "Please configure the API URL in Network Device Scanner Settings."
            )

        try:
            response = requests.post(
                api_url,
                json={"ip": self.ip},
                timeout=30
            )

            # Try to parse JSON response
            try:
                data = response.json()
            except ValueError:
                frappe.log_error(
                    message=response.text,
                    title="Network Scanner Invalid JSON Response"
                )
                frappe.throw(
                    f"Scanner API returned an invalid response. "
                    f"HTTP Status: {response.status_code}"
                )

            if response.status_code == 200:
                return {
                    "status": "success",
                    "mac_address": data.get("mac_address", ""),
                    "vendor": data.get("vendor", ""),
                    "cache_status": data.get("cache_status", ""),
                    "message": data.get(
                        "message",
                        "Device found successfully."
                    )
                }

            return {
                "status": "failed",
                "mac_address": "",
                "vendor": "",
                "cache_status": data.get("cache_status", ""),
                "message": data.get(
                    "message",
                    "Scan failed or device not found."
                )
            }

        except requests.exceptions.ConnectionError:
            frappe.throw(
                f"Could not connect to the scanner API at {api_url}. "
                "Please ensure the service is running."
            )

        except requests.exceptions.Timeout:
            frappe.throw(
                "The scanner API took too long to respond."
            )

        except requests.exceptions.RequestException as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Network Scanner API Request Error"
            )
            frappe.throw(
                f"Scanner API request failed: {str(e)}"
            )

        except Exception as e:
            frappe.log_error(
                message=frappe.get_traceback(),
                title="Network Scanner API Error"
            )
            frappe.throw(
                f"Error: {str(e)}"
            )