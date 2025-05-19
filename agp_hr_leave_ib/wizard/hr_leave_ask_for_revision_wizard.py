from odoo import models, fields, api


class HrLeaveAskForRevisionWizard(models.TransientModel):
    _name = 'hr.leave.ask.for.revision.wizard'
    _description = 'Ask for Revision'

    reason = fields.Text(string="Reason", required=True)

    def action_ask_for_revision(self):
        leave_id = self.env.context.get('active_id')
        leave = self.env['hr.leave'].browse([leave_id])

        if leave:
            query = """
                        UPDATE hr_leave
                        SET state = %s, ask_for_revision_reason = %s
                        WHERE id in %s
                    """
            self.env.cr.execute(query, ('ask_for_revision', self.reason, tuple(leave.ids)))

        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }