/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";


patch(ListController.prototype, "payroll_enh_ib.ListController", {
    setup() {
        this._super();
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.notificationService = useService("notification");
    },

    async onClickMassCreatePayslips() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "wizard.create.mass.payslip",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("payroll_enh_ib.action_wizard_create_mass_payslip");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    }
});