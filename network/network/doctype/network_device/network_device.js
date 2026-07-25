frappe.ui.form.on("Network Device", {
    setup(frm) {

        // Show only enabled device types
        frm.set_query("device_type", function () {
            return {
                filters: {
                    enabled: 1
                }
            };
        });

        // Show only enabled sites
        frm.set_query("site", function () {
            return {
                filters: {
                    enabled: 1
                }
            };
        });

        // Show only enabled tags
        frm.set_query("tag", "tags", function () {
            return {
                filters: {
                    enabled: 1
                }
            };
        });

    }
});