
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RejectWizardPersetujuanAnggaranAGP(models.TransientModel):
    _name = 'pa.reject.wizard'
    _description = 'SPA Rejection Notes'

    reject_reason = fields.Text(string='Alasan Reject', required=True)

    def cancel(self):
        return

    def ok(self):
        active_id = self.env.context.get('active_id')
        pa_model = self.env['account.keuangan.pa'].sudo()

        if active_id:
            pa_id = pa_model.browse([active_id])

            if pa_id:
                pa_id.write({
                    'approval_step': 1,
                    'state': 'rejected',
                })

                for x in pa_id.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()

                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                self.env['spa.approval.line'].create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f"Di-reject oleh {self.env.user.name} sebagai {level_val} dikarenakan: {self.reject_reason}.",
                    'spa_id': pa_id.id,
                })
                    
                for y in pa_id.history_approval_ids.filtered(lambda y: 'Data SPA telah di-submit' in y.note)[0]:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': 4,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.pa')], limit=1).id,
                        'res_id': pa_id.id,
                        'user_id': y.user_id.id,
                        'date_deadline': fields.Date.today() + timedelta(days=2),
                        'state': 'planned',
                        'status': 'todo',
                        'summary': """Harap segera merevisi nilai atau nominal SPA setelah di-reject."""
                    })

        return {'type': 'ir.actions.act_window_close'}