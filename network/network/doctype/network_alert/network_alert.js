frappe.ui.form.on("Network Alert", {
    refresh(frm) {

        if (frm.is_new()) {
            return;
        }

        const acknowledge_types = [
            "Device Down",
            "High Latency",
            "Packet Loss"
        ];

        if (
            frm.doc.acknowledged ||
            !acknowledge_types.includes(frm.doc.alert_type) ||
            !frm.doc.downtime
        ) {
            return;
        }

        frappe.db.get_value(
            "Network Downtime",
            frm.doc.downtime,
            "status"
        ).then((r) => {

            if (!r.message || r.message.status !== "Open") {
                return;
            }

            frm.add_custom_button(
                __("Acknowledge"),
                function () {

                    frappe.confirm(
                        __("Are you sure you want to acknowledge this alert?"),
                        function () {

                            frappe.call({
                                method: "network.network.doctype.network_alert.network_alert.acknowledge",
                                args: {
                                    name: frm.doc.name
                                },
                                freeze: true,
                                freeze_message: __("Acknowledging Alert..."),
                                callback: function (r) {

                                    if (!r.exc) {

                                        frappe.show_alert({
                                            message: __("Alert acknowledged successfully."),
                                            indicator: "green"
                                        });

                                        frm.reload_doc();
                                    }
                                }
                            });

                        }
                    );

                }
            ).addClass("btn-primary");

        });

    }
});