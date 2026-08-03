frappe.listview_settings["Network Device"] = {
    onload(listview) {

        listview.page.add_action_item(__("Disable Devices"), () => {

            const devices = listview.get_checked_items().map(d => d.name);

            if (!devices.length) {
                frappe.msgprint(__("Please select at least one device."));
                return;
            }

            frappe.confirm(
                __("Disable {0} selected devices?", [devices.length]),
                () => {
                    frappe.call({
                        method: "network.api.network_device.disable_devices",
                        args: {
                            devices: devices
                        },
                        callback() {
                            listview.refresh();
                        }
                    });
                }
            );

        });

    }
};