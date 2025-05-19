/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component, useEffect, useRef, onRendered } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

patch(CalendarYearRenderer.prototype, 'agp_hr_leave_lembur_ib.CalendarYearRenderer', {
    onDateClick(info) {
        const targetModel = 'hr.leave.lembur';
        var current_url = window.location.href;
        var myArray = current_url.split("&");
        var current_model = myArray[1].replace('model=', '');

        if (current_model === targetModel) {
            const today = luxon.DateTime.local().toISODate();
            const clickedDate = luxon.DateTime.fromJSDate(info.date).toISODate();
            const yesterday = luxon.DateTime.local().minus({ days: 1 }).toISODate();

            // Check if the clicked date is before H-1 (yesterday)
            if (clickedDate < yesterday) {
                this.env.services.dialog.add(ConfirmationDialog, {
                    title: this.env._t("Invalid Action"),
                    body: this.env._t("Anda hanya dapat mengajukan lembur dari H-1 hingga hari ini dan seterusnya."),
                });
                return;
            }
        }

        this._super(info);
    },
});