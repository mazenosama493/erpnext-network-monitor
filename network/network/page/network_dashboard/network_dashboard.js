
frappe.pages['network-dashboard'].on_page_load = function(wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Live Network Monitor',
        single_column: true
    });

    if ($('#network-dashboard-style').length === 0) {
        $(`
            <style id="network-dashboard-style">
                .network-dashboard {
                    --network-ink: #1f2933;
                    --network-muted: #667085;
                    --network-border: #e4e7ec;
                    --network-accent: #176b87;
                    color: var(--network-ink);
                }

                .network-dashboard-toolbar {
                    display: grid;
                    grid-template-columns: minmax(220px, 1.6fr) repeat(3, minmax(140px, 0.7fr));
                    gap: 10px;
                    align-items: end;
                    padding: 16px;
                    margin-bottom: 18px;
                    background: linear-gradient(135deg, #f7fbfc 0%, #eef5f6 100%);
                    border: 1px solid #dbe8eb;
                    border-radius: 10px;
                }

                .network-filter label {
                    display: block;
                    margin-bottom: 5px;
                    color: var(--network-muted);
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: .06em;
                    text-transform: uppercase;
                }

                .network-filter input,
                .network-filter select {
                    width: 100%;
                    min-height: 36px;
                    padding: 7px 10px;
                    border: 1px solid #cfd8dc;
                    border-radius: 6px;
                    background: #fff;
                    color: var(--network-ink);
                }

                .network-dashboard-summary {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 12px;
                    margin: 0 2px 10px;
                    color: var(--network-muted);
                    font-size: 12px;
                }

                .device-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(min(100%, 330px), 1fr));
                    gap: 14px;
                }

                .device-card {
                    width: auto;
                    max-width: none;
                    min-width: 0;
                    margin: 0;
                    border: 1px solid var(--network-border);
                    border-radius: 10px;
                    box-shadow: 0 3px 12px rgba(31, 41, 51, .06);
                    padding: 16px;
                    background: #fff;
                    box-sizing: border-box;
                    transition: border-color .2s ease, box-shadow .2s ease;
                }

                .device-card:hover {
                    border-color: #9cc6d1;
                    box-shadow: 0 7px 20px rgba(31, 41, 51, .1);
                }

                .device-card.device-card-stale {
                    opacity: .72;
                    border-color: #e4a11b;
                }

                .device-card h4 {
                    gap: 8px;
                    font-size: 15px;
                }

                .device-card h4 > span:first-child {
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                }

                .device-card .device-detail {
                    display: flex;
                    justify-content: space-between;
                    gap: 12px;
                    flex-wrap: wrap;
                }

                .network-empty-state {
                    padding: 42px 20px;
                    border: 1px dashed #cbd5d8;
                    border-radius: 10px;
                    color: var(--network-muted);
                    text-align: center;
                }

                @media (max-width: 900px) {
                    .network-dashboard-toolbar {
                        grid-template-columns: repeat(2, minmax(0, 1fr));
                    }
                }

                @media (max-width: 560px) {
                    .network-dashboard-toolbar {
                        grid-template-columns: 1fr;
                        padding: 12px;
                    }

                    .network-dashboard-summary {
                        align-items: flex-start;
                        flex-direction: column;
                        gap: 3px;
                    }

                    .device-card {
                        padding: 13px;
                    }

                    .device-card .device-detail {
                        align-items: flex-start;
                        flex-direction: column;
                        gap: 2px;
                    }
                }
            </style>
        `).appendTo('head');
    }

    let dashboard = $(`<div class="network-dashboard"></div>`).appendTo(page.main);
    let filterState = { search: '', department: 'ALL' };
    let deviceMetrics = {};
    let deviceDepartments = {};
    let departments = [];

    let toolbar = $(`
        <div class="network-dashboard-toolbar">
            <div class="network-filter">
                <label for="network-device-search">Find a device</label>
                <input id="network-device-search" type="search" placeholder="Search by device, IP or gateway">
            </div>
            <div class="network-filter">
                <label for="network-department-filter">Department</label>
                <select id="network-department-filter"><option value="ALL">All departments</option></select>
            </div>
        </div>
        <div class="network-dashboard-summary">
            <span class="network-results-count">0 devices shown</span>
            <span>Live updates refresh automatically</span>
        </div>
    `).appendTo(dashboard);

    let container = $(`<div class="device-grid"></div>`).appendTo(dashboard);
    let emptyState = $(`<div class="network-empty-state" style="display: none">No devices match these filters.</div>`).appendTo(dashboard);

    let deviceLastSeen = {};

    function refreshDepartmentOptions() {
        let currentValue = filterState.department;
        let availableDepartments = [...new Set([
            ...departments,
            ...Object.values(deviceDepartments).filter(Boolean)
        ])].sort();
        let options = '<option value="ALL">All departments</option>';
        availableDepartments.forEach(department => {
            options += `<option value="${frappe.utils.escape_html(department)}">${frappe.utils.escape_html(department)}</option>`;
        });
        let departmentFilter = toolbar.find('#network-department-filter');
        departmentFilter.html(options).val(availableDepartments.includes(currentValue) ? currentValue : 'ALL');
        filterState.department = departmentFilter.val();
    }

    function applyFilters() {
        let visibleCount = 0;
        container.children('.device-card').each(function() {
            let card = $(this);
            let metrics = deviceMetrics[card.attr('data-device-id')] || {};
            let haystack = [card.attr('data-device-id'), metrics.ip, metrics.gateway, deviceDepartments[card.attr('data-device-id')]]
                .join(' ').toLowerCase();
            let matches = (!filterState.search || haystack.includes(filterState.search)) &&
                (filterState.department === 'ALL' || deviceDepartments[card.attr('data-device-id')] === filterState.department);
            card.toggle(matches);
            if (matches) visibleCount += 1;
        });
        toolbar.find('.network-results-count').text(`${visibleCount} device${visibleCount === 1 ? '' : 's'} shown`);
        emptyState.toggle(visibleCount === 0);
    }

    toolbar.on('input', '#network-device-search', function() {
        filterState.search = $(this).val().trim().toLowerCase();
        applyFilters();
    });
    toolbar.on('change', 'select', function() {
        filterState[$(this).attr('id').replace('network-', '').replace('-filter', '')] = $(this).val();
        applyFilters();
    });

    function loadPCDepartments() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'PCs',
                fields: ['pc_id', 'department'],
                limit_page_length: 0
            },
            callback: function(response) {
                (response.message || []).forEach(pc => {
                    deviceDepartments[pc.pc_id] = pc.department || '';
                });
                refreshDepartmentOptions();
                applyFilters();
            }
        });
    }

    function loadDepartmentOptions() {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'PCs Departments',
                fields: ['name'],
                limit_page_length: 0,
                order_by: 'name asc'
            },
            callback: function(response) {
                departments = (response.message || []).map(department => department.name);
                refreshDepartmentOptions();
                applyFilters();
            }
        });
    }


    function getDeviceCard(deviceId) {
        return $(document.getElementById(`card-${deviceId}`));
    }


    function renderDeviceCard(deviceId, metrics) {

        deviceLastSeen[deviceId] = Date.now();
        deviceMetrics[deviceId] = metrics || {};
        if (getDeviceCard(deviceId).length === 0) {

            let cardHtml = `
                <div id="card-${deviceId}" data-device-id="${frappe.utils.escape_html(deviceId)}" class="panel panel-default device-card">

                    <h4 style="
                        margin-top: 0;
                        border-bottom: 1px solid #eee;
                        padding-bottom: 10px;
                        font-weight: bold;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <span>🖥️ ${deviceId}</span>

                        <span
                            class="status-badge"
                            style="
                                font-size: 11px;
                                padding: 2px 8px;
                                border-radius: 12px;
                                background: #eee;
                                color: #333;
                            "
                        >
                            --
                        </span>
                    </h4>


                    <div style="font-size: 12px; line-height: 1.9;">

                        <div style="
                            color: #555;
                            background: #f8f9fa;
                            padding: 6px 8px;
                            border-radius: 4px;
                            margin-bottom: 8px;
                        ">
                            <b>Interface:</b>
                            <span class="net-interface">--</span>
                            <br>

                            <b>IP:</b>
                            <span class="net-ip">--</span>

                            |

                            <b>Speed:</b>
                            <span class="link-speed">--</span> Mbps
                        </div>


                        <div style="
                            display: flex;
                            justify-content: space-between;
                        ">
                            <b>
                                Gateway (<span class="gw-ip">N/A</span>):
                            </b>

                            <span>
                                <span class="gateway-ping">--</span>
                                |
                                Loss:
                                <span class="gateway-loss">--</span>%
                                |
                                Jitter:
                                <span class="gateway-jitter">--</span>ms
                            </span>
                        </div>


                        <div style="
                            display: flex;
                            justify-content: space-between;
                        ">
                            <b>Internet :</b>

                            <span>
                                <span class="internet-ping">--</span>
                                |
                                Loss:
                                <span class="internet-loss">--</span>%
                            </span>
                        </div>


                        <div style="
                            display: flex;
                            justify-content: space-between;
                        ">
                            <b>DNS :</b>

                            <span class="dns-status">--</span>
                        </div>


                        <div style="
                            display: flex;
                            justify-content: space-between;
                        ">
                            <b>TCP :</b>

                            <span class="tcp-status">--</span>
                        </div>


                        <div style="
                            border-top: 1px dashed #eee;
                            margin-top: 6px;
                            padding-top: 6px;
                        ">

                            <div>
                                <b>Status Reason:</b>
                                <span
                                    class="status-reason"
                                    style="color: #666;"
                                >
                                    --
                                </span>
                            </div>

                            <div>
                                <b>Last Update:</b>
                                <span
                                    class="last-update"
                                    style="color: #888;"
                                >
                                    --
                                </span>
                            </div>

                        </div>


                        <div
                            class="downtime-box"
                            style="
                                display: none;
                                background: #fff3cd;
                                color: #856404;
                                padding: 4px 8px;
                                border-radius: 4px;
                                margin-top: 6px;
                                font-weight: bold;
                            "
                        >
                            ⚠️ Downtime Active
                            (Start:
                            <span class="downtime-start">--</span>)
                        </div>


                        <hr style="margin: 8px 0;">


                        <div style="
                            text-align: center;
                            font-weight: bold;
                            font-size: 13px;
                        ">

                            <span style="color: #28a745;">
                                ⬇️
                                <span class="download-speed">0.00</span>
                                Mbps
                            </span>

                            |

                            <span style="color: #007bff;">
                                ⬆️
                                <span class="upload-speed">0.00</span>
                                Mbps
                            </span>

                        </div>

                    </div>

                </div>
            `;

            container.append(cardHtml);
        }


        let card = getDeviceCard(deviceId);

        card
            .removeClass('device-card-stale')
            .removeAttr('title');


        card.find('.net-interface')
            .text(metrics.interface || 'N/A');

        card.find('.net-ip')
            .text(metrics.ip || 'N/A');

        card.find('.link-speed')
            .text(metrics.link_speed || 0);

        card.find('.gw-ip')
            .text(metrics.gateway || 'N/A');


        let status = metrics.status || 'UNKNOWN';

        let reason = metrics.status_reason || '';

        card.find('.status-reason')
            .text(reason);


        let badgeColor =
            status === 'ONLINE'
                ? '#d4edda'
                : (
                    status === 'STARTING'
                        ? '#fff3cd'
                        : '#f8d7da'
                );

        let textColor =
            status === 'ONLINE'
                ? '#155724'
                : (
                    status === 'STARTING'
                        ? '#856404'
                        : '#721c24'
                );


        card.find('.status-badge')
            .text(status)
            .css({
                'background-color': badgeColor,
                'color': textColor
            });


        let gwPing = metrics.gateway_latency;

        card.find('.gateway-ping').text(
            gwPing !== null && gwPing !== undefined
                ? `${gwPing} ms`
                : 'Timeout'
        );


        card.find('.gateway-loss').text(
            metrics.gateway_packet_loss !== null
                ? metrics.gateway_packet_loss
                : '0'
        );


        card.find('.gateway-jitter').text(
            metrics.gateway_jitter !== null
                ? metrics.gateway_jitter
                : '0'
        );


        let netPing = metrics.internet_latency;

        card.find('.internet-ping').text(
            netPing !== null && netPing !== undefined
                ? `${netPing} ms`
                : 'Timeout'
        );


        card.find('.internet-loss').text(
            metrics.internet_packet_loss !== null
                ? metrics.internet_packet_loss
                : '0'
        );


        let dnsOk = metrics.dns === true;

        let dnsTime =
            metrics.dns_latency !== null &&
            metrics.dns_latency !== undefined
                ? ` (${metrics.dns_latency} ms)`
                : '';

        let dnsIp =
            metrics.dns_resolved_ip &&
            metrics.dns_resolved_ip !== 'N/A'
                ? ` [${metrics.dns_resolved_ip}]`
                : '';


        card.find('.dns-status').text(
            dnsOk
                ? `✅ Pass${dnsTime}${dnsIp}`
                : '❌ Fail'
        );


        let tcpOk = metrics.tcp_443 === true;

        let tcpTime =
            metrics.tcp_443_latency !== null &&
            metrics.tcp_443_latency !== undefined
                ? ` (${metrics.tcp_443_latency} ms)`
                : '';


        card.find('.tcp-status').text(
            tcpOk
                ? `✅ Pass${tcpTime}`
                : '❌ Fail'
        );


        card.find('.last-update').text(
            metrics.last_update
                ? metrics.last_update
                : 'N/A'
        );


        if (metrics.downtime_active) {

            card.find('.downtime-box').show();

            card.find('.downtime-start').text(
                metrics.downtime_start || 'Just now'
            );

        } else {

            card.find('.downtime-box').hide();

        }


        let downSpeed =
            metrics.download !== undefined
                ? metrics.download
                : 0.00;

        let upSpeed =
            metrics.upload !== undefined
                ? metrics.upload
                : 0.00;


        card.find('.download-speed')
            .text(Number(downSpeed).toFixed(2));

        card.find('.upload-speed')
            .text(Number(upSpeed).toFixed(2));

        applyFilters();
    }


    // Initial data load from Redis
    function refreshLiveDevices() {

        frappe.call({
            method: "network.api.devices_api.get_active_devices",

            callback: function(r) {

                if (r && r.message) {

                    r.message.forEach(item => {

                        renderDeviceCard(
                            item.device_id,
                            item.metrics
                        );

                    });

                    loadPCDepartments();
                    loadDepartmentOptions();
                }
            }
        });
    }


    // Load existing devices when dashboard opens
    refreshLiveDevices();
    loadDepartmentOptions();
    setInterval(loadDepartmentOptions, 30000);


    // Handle Socket.IO live updates
    function handleLiveNetworkUpdate(incoming) {

        let data = incoming;

        if (incoming && incoming.message) {
            data = incoming.message;
        }


        if (typeof data === 'string') {

            try {
                data = JSON.parse(data);
            } catch (e) {
                console.error(
                    'Invalid live network update:',
                    e
                );
                return;
            }
        }


        if (!data || !data.device_id) {
            return;
        }


        let metrics = data.metrics;


        if (typeof metrics === 'string') {

            try {
                metrics = JSON.parse(metrics);
            } catch (e) {
                console.error(
                    'Invalid metrics:',
                    e
                );

                metrics = {};
            }
        }


        if (metrics) {

            console.log(
                '🔥 LIVE NETWORK UPDATE:',
                data.device_id,
                metrics
            );

            renderDeviceCard(
                data.device_id,
                metrics
            );
        }
    }


    // Register the realtime listener directly.
    // No waiting for frappe.realtime.socket.
    frappe.realtime.on(
        'live_network_update',
        handleLiveNetworkUpdate
    );


    // Mark devices stale if no update is received
    // for more than 5 seconds.
    setInterval(function() {

        let now = Date.now();

        for (let deviceId in deviceLastSeen) {

            if (
                now - deviceLastSeen[deviceId] > 5000
            ) {

                getDeviceCard(deviceId)
                    .addClass('device-card-stale')
                    .attr(
                        'title',
                        'No live update received in the last 5 seconds'
                    );
            }
        }

    }, 1000);

};

