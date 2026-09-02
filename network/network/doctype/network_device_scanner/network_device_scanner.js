
frappe.ui.form.on('Network Device Scanner', {

    onload: function(frm) {

        // Clear ALL previous scanner data
        frm.set_value('ip', '');
        frm.set_value('mac_address', '');
        frm.set_value('vendor', '');
        frm.set_value('cache_status', '');
        frm.set_value('message', '');

        // Clear dashboard headline
        frm.dashboard.clear_headline();

        // Clear any dirty state caused by clearing fields
        frm.doc.__islocal = 1;
    },

    refresh: function(frm) {

        // Disable Save
        frm.disable_save();

        // Clear dashboard
        frm.dashboard.clear_headline();
    },

    scan_button: function(frm) {

        if (!frm.doc.ip) {
            frappe.msgprint(
                __('Please enter the IP address before scanning.')
            );
            return;
        }

        // Clear previous results before scanning
        frm.set_value('mac_address', '');
        frm.set_value('vendor', '');
        frm.set_value('cache_status', '');
        frm.set_value('message', '');

        // Show scanning message
        frm.dashboard.set_headline(
            __('Scanning network for device...')
        );

        frm.call({
            doc: frm.doc,
            method: 'fetch_device_info',
            freeze: true,
            freeze_message: __('Scanning network...'),

            callback: function(r) {

                if (!r.message) {
                    frm.dashboard.set_headline(
                        `<div class="text-danger" style="font-weight:bold;">
                            <i class="fa fa-times"></i>
                            ${__('No response received from scanner.')}
                        </div>`
                    );
                    return;
                }

                const data = r.message;

                // Update fields with scanner result
                frm.set_value(
                    'mac_address',
                    data.mac_address || ''
                );

                frm.set_value(
                    'vendor',
                    data.vendor || ''
                );

                frm.set_value(
                    'cache_status',
                    data.cache_status || ''
                );

                frm.set_value(
                    'message',
                    data.message || ''
                );

                // Display result
                if (data.status === 'success') {

                    frm.dashboard.set_headline(
                        `<div class="text-success" style="font-weight:bold;">
                            <i class="fa fa-check"></i>
                            ${frappe.utils.escape_html(
                                data.message || __('Device found successfully.')
                            )}
                        </div>`
                    );

                } else {

                    frm.dashboard.set_headline(
                        `<div class="text-danger" style="font-weight:bold;">
                            <i class="fa fa-times"></i>
                            ${frappe.utils.escape_html(
                                data.message || __('Device not found.')
                            )}
                        </div>`
                    );
                }
            }
        });
    }
});
