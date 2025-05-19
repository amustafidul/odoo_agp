from odoo import models, fields, api


class LemburAskForRevisionWizard(models.TransientModel):
    _name = 'lembur.ask.for.revision.wizard'
    _description = 'Ask for Revision'

    reason = fields.Text(string="Reason", required=True)

    def action_ask_for_revision(self):
        obj_id = self.env.context.get('active_id')
        obj = self.env['hr.leave.lembur'].browse([obj_id])

        if obj:
            query = """
                        UPDATE hr_leave_lembur
                        SET state = %s, ask_for_revision_reason = %s
                        WHERE id in %s
                    """
            self.env.cr.execute(query, ('ask_for_revision', self.reason, tuple(obj.ids)))