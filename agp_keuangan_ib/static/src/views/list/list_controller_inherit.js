/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useService } from "@web/core/utils/hooks";


patch(ListController.prototype, "agp_keuangan_ib.ListController", {
    setup() {
        this._super();
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.notificationService = useService("notification");
        this.user = useService("user");
    },
    
    async onClickExportBankGaransi() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "bank.garansi.export.wizard",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_keuangan_ib.action_open_export_wizard");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },
    
    async onClickExportSinkingFund() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "sinking.fund.export.wizard",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_keuangan_ib.action_open_export_sinking_wizard");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },

    async onClickGenerateKonsolidasiRkap() {
        try {
            const userInfo = await this.rpc('/api/user/groups');
            if (userInfo.is_eligible) {
                this.actionService.doAction("agp_report_extended.action_generate_konsolidasi");
            } else {
                this.notificationService.add("Anda tidak berhak untuk mencetak laporan RKAP Konsolidasi Cabang. Silakan hubungi Administrator!", { 
                    type: "danger",
                    sticky: false  // Makes the notification stay until dismissed
                });
                return false;  // Prevent further execution
            }
        } catch (error) {
            this.notificationService.add("Terjadi kesalahan saat memeriksa izin akses. Silakan coba lagi atau hubungi Administrator.", { 
                type: "danger",
                sticky: true
            });
            console.error(error);  // Log the error for debugging
            return false;
        }
    },

    async onClickExportDeposito() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "deposito.export.wizard",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_keuangan_ib.action_open_export_deposito_wizard");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },

    async onClickExportShl() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "shl.export.wizard",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_keuangan_ib.action_open_export_shl_wizard");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },
    
    async onClickExportNp() {
        try {
            const action = {
                type: "ir.actions.act_window",
                res_model: "np.export.wizard",
                view_mode: "form",
                target: "new",
            };

            this.actionService.doAction("agp_keuangan_ib.action_open_export_np_wizard");
        } catch (error) {
            this.env.services.notification.add(`An error occurred: ${error.message}`, { type: "danger" });
        }
    },
    
});

