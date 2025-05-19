/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { TimeOffCalendarController } from "@hr_holidays/views/calendar/calendar_controller";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { serializeDate } from "@web/core/l10n/dates";


patch(TimeOffCalendarController.prototype, 'agp_employee_ib.TimeOffCalendarController', {
    newTimeOffRequest() {
        const context = {};

        if (this.employeeId) {
            context['default_employee_id'] = this.employeeId;
        }
        if (this.model.meta.scale === 'day') {
            context['default_date_from'] = serializeDate(
                this.model.data.range.start.set({ hours: 7 }), "datetime"
            );
            context['default_date_to'] = serializeDate(
                this.model.data.range.end.set({ hours: 19 }), "datetime"
            );
        }

        const customTitle = this.env._t('New Leaves');

        this.displayDialog(FormViewDialog, {
            resModel: 'hr.leave',
            title: customTitle,
            viewId: this.model.formViewId,
            onRecordSaved: () => {
                this.model.load();
                this.env.timeOffBus.trigger('update_dashboard');
            },
            context: context,
        });
    }
});