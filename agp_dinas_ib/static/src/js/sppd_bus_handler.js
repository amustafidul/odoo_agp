odoo.define('agp_dinas_ib.SppdBusNotificationHandler', function (require) {
    "use strict";

    const BusService = require('bus.BusService');
    const { useService } = require("@web/core/utils/hooks");
    const { registry } = require("@web/core/registry");
    const { Component, useEffect } = owl;

    // The modern Odoo 16 way to global services is with the right patch or service.
    // For this example, we will try to patch the core BusService client handler if possible,
    // or create a component that listens.
    // Easier for initial integration is to use a service registry for notifications.

    const userBusService = registry.category("services").get("bus_service");
    const notificationService = registry.category("services").get("notification");
    const actionService = registry.category("services").get("action");
    const core = require('web.core');
    const _t = core._t;

    if (userBusService) {
        userBusService.addEventListener('notification', ({ detail: notifications }) => {
            for (const notification of notifications) {
                // Bus.bus notifications can come in the format of an array [channel, message]
                // or directly as a message if the channel is already known.
                // Let's assume the message structure of _sendone(channel, type, payload) is:
                // notification.type = 'sppd_extension_custom_alert' (from the 2nd argument of _sendone)
                // notification.payload = payload (from the 3rd argument of _sendone)

                let message_type = '';
                let message_payload = {};

                if (Array.isArray(notification) && notification.length === 2) {
                    // This is the format [channel, {type: 'xxx', payload: {...}}]
                    // Or [channel, direct_payload_if_type_is_passed_to_sendone]
                    // We adjust it with _sendone(channel, message_type_custom, bus_payload)
                    // where message_type_custom is 'sppd_extension_custom_alert'
                    // and bus_payload is the payload.
                    // So, notification in JS will have notif.type and notif.payload
                    message_type = notification.type;
                    message_payload = notification.payload;
                } else if (notification.type && notification.payload) {
                     // If the notification directly contains type and payload (common structure in Odoo 16 bus_service)
                    message_type = notification.type;
                    message_payload = notification.payload;
                }


                if (message_type === 'sppd_extension_custom_alert') {
                    _logger.info('Received sppd_extension_custom_alert:', message_payload);

                    let buttons = [];
                    if (message_payload.sppd_url || message_payload.sppd_id) {
                        buttons.push({
                            name: _t('Lihat SPPD'),
                            primary: true,
                            onClick: () => {
                                if (message_payload.sppd_url && message_payload.sppd_url.includes("/web#")) {
                                    window.location.href = message_payload.sppd_url;
                                } else if (message_payload.sppd_id) {
                                    actionService.doAction({
                                        type: 'ir.actions.act_window',
                                        res_model: 'hr.leave.dinas',
                                        res_id: message_payload.sppd_id,
                                        views: [[false, 'form']],
                                        target: 'current',
                                    });
                                }
                            }
                        });
                    }

                    notificationService.add(message_payload.message || _t("Ada permintaan perpanjangan SPPD baru."), {
                        title: message_payload.title || _t("Notifikasi Perpanjangan SPPD"),
                        type: 'info', // 'info', 'warning', 'danger', 'success'
                        sticky: message_payload.sticky !== undefined ? message_payload.sticky : true,
                        className: message_payload.className || '',
                        buttons: buttons,
                    });
                }
            }
        });
        _logger.info("SPPD Custom Bus Notification Handler Loaded and Listening.");
    } else {
        _logger.warning("BusService not available for SPPD Custom Notifications.");
    }
});