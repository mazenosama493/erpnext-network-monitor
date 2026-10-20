frappe.pages['network-topology'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Network Topology Maps',
        single_column: true
    });

    $(wrapper).find('.layout-main-section').html(`
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; background: #2d2d2d; padding: 10px 15px; border-radius: 6px;">
            <div style="display: flex; align-items: center; gap: 10px; width: 100%;">
                <label style="color: #fff; font-weight: 600; margin: 0; white-space: nowrap;">Select Map:</label>
                <select id="map-selector" class="form-control" style="max-width: 350px; background: #1e1e1e; color: #fff; border: 1px solid #444;"></select>
            </div>
        </div>

        <div id="topology-wrapper" style="position: relative; width: 100%; height: 78vh; background: #1e1e1e; border-radius: 8px; overflow: hidden; border: 1px solid #333;">
            <div style="position: absolute; top: 16px; right: 16px; z-index: 10; background: #ffffff; color: #111; padding: 12px 18px; border-radius: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); font-size: 13px; min-width: 190px;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <div style="width: 70px; height: 0; border-top: 3px solid #22c55e; margin-right: 14px;"></div>
                    <strong>Cable</strong>
                </div>
                <div style="display: flex; align-items: center;">
                    <div style="width: 70px; height: 0; border-top: 3px dashed #22c55e; margin-right: 14px;"></div>
                    <strong>Wireless</strong>
                </div>
            </div>

            <div id="node-info-box" style="display: none; position: absolute; bottom: 16px; left: 16px; z-index: 10; background: rgba(20, 20, 20, 0.94); color: #f3f4f6; padding: 14px 18px; border-radius: 6px; border: 1px solid #444; font-size: 12px; min-width: 260px; box-shadow: 0 4px 15px rgba(0,0,0,0.6);"></div>

            <div id="vis-canvas" style="width: 100%; height: 100%;"></div>
        </div>
    `);

    let network = null;
    let editMode = false;
    let currentMapName = null;
    let nodeStateMap = {};
    let availableDevicesList = [];
    let nodesDataSet = null;
    let edgesDataSet = null;

    const $editBtn = page.add_inner_button(__('Edit Map: OFF'), () => {
        editMode = !editMode;
        $editBtn.text(editMode ? __('Edit Map: ON (Drag Enabled)') : __('Edit Map: OFF'));
        $editBtn.toggleClass('btn-primary', editMode);
        if (network) {
            network.setOptions({ interaction: { dragNodes: editMode } });
        }
    });

    page.add_inner_button(__('Save Positions'), () => {
        if (!network || !currentMapName) return;
        const positions = network.getPositions();
        const posArray = Object.keys(positions).map(id => ({
            id: id,
            x: positions[id].x,
            y: positions[id].y
        }));
        frappe.call({
            method: 'network.network.page.network_topology.network_topology.save_map_positions',
            args: { map_name: currentMapName, positions: posArray },
            callback: () => frappe.show_alert({ message: __('Node coordinates saved successfully'), indicator: 'green' })
        });
    });

    page.add_inner_button(__('Add Device'), () => openAddDeviceDialog());
    page.add_inner_button(__('Connect Devices'), () => openAddLinkDialog());

    page.add_inner_button(__('Delete Selection'), () => {
        if (!network || !currentMapName) return;
        const selectedNodes = network.getSelectedNodes();
        const selectedEdges = network.getSelectedEdges();

        if (selectedNodes.length) {
            const deviceId = selectedNodes[0];
            frappe.confirm(__('Remove device {0} from this map?', [deviceId]), () => {
                frappe.call({
                    method: 'network.network.page.network_topology.network_topology.remove_device_from_map',
                    args: { map_name: currentMapName, device: deviceId },
                    callback: () => loadMapTopology(currentMapName, true)
                });
            });
        } else if (selectedEdges.length) {
            const linkId = selectedEdges[0];
            frappe.confirm(__('Delete this connection link?'), () => {
                frappe.call({
                    method: 'network.network.page.network_topology.network_topology.remove_link_from_map',
                    args: { map_name: currentMapName, link_id: linkId },
                    callback: () => loadMapTopology(currentMapName, true)
                });
            });
        } else {
            frappe.msgprint(__('Please click a device node or connection line on the map first to select it.'));
        }
    });

    function buildDeviceSvgDataUri(deviceType, visualState, typeIcon, topologyIcon) {
        let badgeColor = '#6b7280';
        let badgeSymbol = '?';

        if (visualState === 'Online') {
            badgeColor = '#22c55e';
            badgeSymbol = '✓';
        } else if (visualState === 'Warning') {
            badgeColor = '#f59e0b';
            badgeSymbol = '!';
        } else if (visualState === 'Offline') {
            badgeColor = '#ef4444';
            badgeSymbol = '✕';
        }

        let bodyContent = '';

        // 1. Primary: Use the attached `topology_icon` image if available
        if (topologyIcon) {
            bodyContent = `
                <image href="${topologyIcon}" x="8" y="10" width="44" height="44" preserveAspectRatio="xMidYMid meet"/>
            `;
        } else {
            // 2. Fallback: Built-in SVG icon based on `icon` / `device_type`
            const iconStr = ((typeIcon || '') + ' ' + (deviceType || '')).toLowerCase();
            let innerGraphic = '';

            if (iconStr.includes('router') || iconStr.includes('wifi')) {
                innerGraphic = `
                    <ellipse cx="32" cy="34" rx="14" ry="7" fill="#334155" stroke="#38bdf8" stroke-width="1.5"/>
                    <path d="M22 34v-6c0-4 20-4 20 0v6" fill="none" stroke="#38bdf8" stroke-width="1.5"/>
                    <circle cx="32" cy="30" r="1.5" fill="#38bdf8"/>
                `;
            } else if (iconStr.includes('shield') || iconStr.includes('lock') || iconStr.includes('firewall') || iconStr.includes('fw')) {
                innerGraphic = `
                    <path d="M32 20l10 4v8c0 7-10 12-10 12s-10-5-10-12v-8l10-4z" fill="#1e293b" stroke="#38bdf8" stroke-width="1.5"/>
                `;
            } else if (iconStr.includes('cloud') || iconStr.includes('isp')) {
                innerGraphic = `
                    <path d="M24 38h16a6 6 0 0 0 1-11.9A8 8 0 0 0 25 23a7 7 0 0 0-1 15z" fill="#1e293b" stroke="#38bdf8" stroke-width="1.5"/>
                `;
            } else {
                innerGraphic = `
                    <rect x="20" y="24" width="24" height="16" rx="2" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5"/>
                    <circle cx="25" cy="32" r="1.5" fill="#22c55e"/>
                    <circle cx="30" cy="32" r="1.5" fill="#38bdf8"/>
                    <line x1="34" y1="32" x2="39" y2="32" stroke="#64748b" stroke-width="1.5"/>
                `;
            }

            bodyContent = `
                <rect x="10" y="14" width="44" height="36" rx="6" fill="#1e293b" stroke="#475569" stroke-width="2"/>
                ${innerGraphic}
            `;
        }

        const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
            ${bodyContent}
            <circle cx="50" cy="14" r="10" fill="${badgeColor}" stroke="#1e1e1e" stroke-width="2"/>
            <text x="50" y="18" font-family="Arial, sans-serif" font-size="13" font-weight="bold" fill="#ffffff" text-anchor="middle">${badgeSymbol}</text>
        </svg>`;

        return 'data:image/svg+xml;utf8,' + encodeURIComponent(svg);
    }

    function computeEdgeColor(sourceId, targetId) {
        const s = nodeStateMap[sourceId] || 'Unknown';
        const t = nodeStateMap[targetId] || 'Unknown';
        if (s === 'Offline' || t === 'Offline') return '#ef4444';
        if (s === 'Warning' || t === 'Warning' || s === 'Unknown' || t === 'Unknown') return '#eab308';
        return '#22c55e';
    }

    function loadMapsList() {
        frappe.call({
            method: 'network.network.page.network_topology.network_topology.get_maps',
            callback: (r) => {
                if (!r.message || !r.message.length) return;
                const maps = r.message;
                const $selector =$('#map-selector');
                $selector.empty();

                maps.forEach(m => {
                    $selector.append(`<option value="${m.name}" ${m.is_default ? 'selected' : ''}>${m.map_name}</option>`);
                });

                currentMapName = $selector.val();
                loadMapTopology(currentMapName, false);

                $selector.off('change').on('change', function() {
                    currentMapName = $(this).val();
                    loadMapTopology(currentMapName, false);
                });
            }
        });
    }

    function loadMapTopology(mapName, preserveViewport) {
        frappe.call({
            method: 'network.network.page.network_topology.network_topology.get_map_topology',
            args: { map_name: mapName },
            callback: (r) => {
                if (!r.message) return;
                const { nodes, links, available_devices } = r.message;
                nodeStateMap = {};
                availableDevicesList = available_devices;

                const visNodes = [];
                nodes.forEach(n => {
                    nodeStateMap[n.id] = n.visual_state;
                    visNodes.push({
                        id: n.id,
                        label: n.label,
                        x: n.x,
                        y: n.y,
                        shape: 'image',
                        image: buildDeviceSvgDataUri(n.device_type, n.visual_state, n.type_icon, n.topology_icon),
                        font: { color: '#e5e7eb', size: 12, face: 'Arial', vadjust: 6 },
                        data: n
                    });
                });

                const visEdges = [];
                links.forEach(l => {
                    visEdges.push({
                        id: l.id,
                        from: l.source_device,
                        to: l.target_device,
                        color: { color: computeEdgeColor(l.source_device, l.target_device) },
                        width: 2,
                        dashes: l.connection_type === 'Wireless'
                    });
                });

                renderGraph(visNodes, visEdges, preserveViewport);
            }
        });
    }

    function renderGraph(visNodes, visEdges, preserveViewport) {
        const container = document.getElementById('vis-canvas');
        
        nodesDataSet = new vis.DataSet(visNodes);
        edgesDataSet = new vis.DataSet(visEdges);

        const data = { nodes: nodesDataSet, edges: edgesDataSet };
        const options = {
            nodes: {
                borderWidth: 0,
                size: 30
            },
            edges: {
                smooth: { type: 'continuous' }
            },
            physics: { enabled: false },
            interaction: {
                dragNodes: editMode,
                hover: true
            }
        };

        if (network) {
            const scale = network.getScale();
            const position = network.getViewPosition();
            network.destroy();
            network = new vis.Network(container, data, options);
            if (preserveViewport) {
                network.moveTo({ position: position, scale: scale });
            }
        } else {
            network = new vis.Network(container, data, options);
        }

        network.on('click', function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                const nodeObj = nodesDataSet.get(nodeId);
                const d = nodeObj.data;
                const $box =$('#node-info-box');
                $box.html(`
                    <div style="font-size: 14px; font-weight: bold; margin-bottom: 4px; color: #60a5fa;">${d.label} (${d.id})</div>
                    <div><strong>IP:</strong> ${d.ip_address} | <strong>Type:</strong> ${d.device_type}</div>
                    <div><strong>State:</strong> ${d.visual_state} | <strong>Ping:</strong> ${d.response_time} ms | <strong>Loss:</strong> ${d.packet_loss}%</div>
                    ${d.downtime_reason ? `<div style="color:#f87171; margin-top:4px;"><strong>Downtime:</strong> ${d.downtime_reason} (Since${d.downtime_started})</div>` : ''}
                    <div style="margin-top: 6px;">
                        <a href="/app/network-device/${encodeURIComponent(d.id)}" style="color: #93c5fd; text-decoration: underline;">Open Device Form →</a>
                    </div>
                `).fadeIn(150);
            } else {
                $('#node-info-box').fadeOut(150);
            }
        });
    }

    function openAddDeviceDialog() {
        const options = availableDevicesList.map(d => ({ label: `${d.device_name} (${d.ip_address})`, value: d.name }));
        options.unshift({ label: __('-- Add All Unplaced Devices --'), value: '__ALL__' });

        const d = new frappe.ui.Dialog({
            title: __('Add Device to Map'),
            fields: [
                { fieldname: 'device', label: __('Select Device'), fieldtype: 'Select', options: options, reqd: 1 }
            ],
            primary_action_label: __('Add to Map'),
            primary_action(values) {
                frappe.call({
                    method: 'network.network.page.network_topology.network_topology.add_device_to_map',
                    args: { map_name: currentMapName, device: values.device },
                    callback: () => {
                        d.hide();
                        loadMapTopology(currentMapName, true);
                    }
                });
            }
        });
        d.show();
    }

    function openAddLinkDialog() {
        const d = new frappe.ui.Dialog({
            title: __('Connect Two Devices'),
            fields: [
                { fieldname: 'source_device', label: __('Source Device'), fieldtype: 'Link', options: 'Network Device', reqd: 1 },
                { fieldname: 'target_device', label: __('Target Device'), fieldtype: 'Link', options: 'Network Device', reqd: 1 },
                { fieldname: 'connection_type', label: __('Connection Type'), fieldtype: 'Select', options: 'Cable\nWireless', default: 'Cable', reqd: 1 },
                { fieldname: 'source_port', label: __('Source Port (Optional)'), fieldtype: 'Data' },
                { fieldname: 'target_port', label: __('Target Port (Optional)'), fieldtype: 'Data' }
            ],
            primary_action_label: __('Establish Link'),
            primary_action(values) {
                frappe.call({
                    method: 'network.network.page.network_topology.network_topology.add_link_to_map',
                    args: Object.assign({ map_name: currentMapName }, values),
                    callback: () => {
                        d.hide();
                        loadMapTopology(currentMapName, true);
                    }
                });
            }
        });
        d.show();
    }

    frappe.realtime.on("network_device_status_update", (data) => {
        if (!nodesDataSet || !edgesDataSet) return;

        const node = nodesDataSet.get(data.device);
        if (!node) return;

        let visualState = data.status || "Unknown";
        if (data.status === "Online" && (data.packet_loss > 0 || data.response_time > 150)) {
            visualState = "Warning";
        }

        node.data.status = data.status;
        if (data.ip_address) {
            node.data.ip_address = data.ip_address;
        }
        node.data.visual_state = visualState;
        node.data.response_time = data.response_time;
        node.data.packet_loss = data.packet_loss;
        node.image = buildDeviceSvgDataUri(
            node.data.device_type,
            visualState,
            node.data.type_icon,
            node.data.topology_icon
        );

        nodesDataSet.update(node);
        nodeStateMap[data.device] = visualState;

        const connectedEdges = edgesDataSet.get({
            filter: function (edge) {
                return edge.from === data.device || edge.to === data.device;
            }
        });

        connectedEdges.forEach(edge => {
            edge.color = { color: computeEdgeColor(edge.from, edge.to) };
            edgesDataSet.update(edge);
        });
    });

    frappe.require('https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/dist/vis-network.min.js', () => {
        loadMapsList();
    });
};