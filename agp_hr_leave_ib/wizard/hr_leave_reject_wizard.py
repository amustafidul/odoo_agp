from odoo import models, fields, api


class HrLeaveRejectWizard(models.TransientModel):
    _name = 'hr.leave.reject.wizard'
    _description = 'Leave Rejection Wizard'

    reason = fields.Text(string="Rejection Reason", required=True)

    def action_reject_leave(self):
        leave_id = self.env.context.get('active_id')
        leave = self.env['hr.leave'].browse([leave_id])

        if leave:
            query = """
                                    UPDATE hr_leave
                                    SET state = %s, rejection_reason = %s
                                    WHERE id in %s
                                """
            self.env.cr.execute(query, ('rejected', self.reason, tuple(leave.ids)))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }