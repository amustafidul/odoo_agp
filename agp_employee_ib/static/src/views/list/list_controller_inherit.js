/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";


patch(ListController.prototype, "agp_employee_ib.ListController", {
    setup() {
        this._super();
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.notificationService = useService("notification");
    },

    async onClickGetHolidayData() {
        try {
            const result = await this.rpc("/agp_employee_ib/get_holiday_data", {});
            console.log('result', result);
            if (result.success) {
                this.notificationService.add("Data fetched successfully!", { type: "success" });
                location.reload();
            } else {
                this.notificationService.add("Failed to fetch data.", { type: "danger" });
            }
        } catch (error) {
            this.notificationService.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },

    async onClickBulkUploadAttachment() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "hr.employee.bulk.upload.attachment.wizard",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_employee_ib.action_bulk_upload_attachment_wizard");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },

    async onClickBulkImportData() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "wizard.import.employee",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_employee_ib.action_wizard_import_employee");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    }
});