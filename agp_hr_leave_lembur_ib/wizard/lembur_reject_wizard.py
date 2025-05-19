from odoo import models, fields, api


class LemburRejectWizard(models.TransientModel):
    _name = 'lembur.reject.wizard'
    _description = 'Rejection Wizard for Lembur'

    reason = fields.Text(string="Rejection Reason", required=True)

    def action_reject(self):
        obj_id = self.env.context.get('active_id')
        obj = self.env['hr.leave.lembur'].browse([obj_id])

        if obj:
            query = """
                                    UPDATE hr_leave_lembur
                                    SET state = %s, rejection_reason = %s
                                    WHERE id in %s
                                """
            self.env.cr.execute(query, ('rejected', self.reason, tuple(obj.ids)))