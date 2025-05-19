
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class RejectWizardAGP(models.TransientModel):
    _name = 'kkhc.reject.wizard'
    _description = 'KKHC Rejection Notes'

    reject_reason = fields.Text(string='Alasan Reject', required=True)

    def cancel(self):
        return

    def ok(self):
        # groups_id = self.env.context.get('groups_id')
        active_id = self.env.context.get('active_id')
        kkhc_model = self.env['account.keuangan.kkhc'].sudo()

        if active_id:
            kkhc_id = kkhc_model.browse([active_id])

            if kkhc_id:
                for doc_line in kkhc_id.document_ids:
                    doc_line.state = 'rejected'

                kkhc_id.write({
                    'approval_step': 1,
                    'state': 'rejected',
                })

                for x in kkhc_id.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()

                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                self.env['kkhc.approval.line'].create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f"Di-reject oleh {self.env.user.name} sebagai {level_val} dikarenakan: {self.reject_reason}.",
                    'kkhc_id': kkhc_id.id,
                })
                    
                for y in kkhc_id.history_approval_ids.filtered(lambda y: 'Data KKHC telah di-submit' in y.note)[0]:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': 4,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.kkhc')], limit=1).id,
                        'res_id': kkhc_id.id,
                        'user_id': y.user_id.id,
                        'date_deadline': fields.Date.today() + timedelta(days=2),
                        'state': 'planned',
                        'status': 'todo',
                        'summary': """Harap segera merevisi nilai atau nominal KKHC setelah di-reject."""
                    })

        return {'type': 'ir.actions.act_window_close'}
    
class RejectWizardAGPRKAP(models.TransientModel):
    _name = 'rkap.reject.wizard'
    _description = 'RKAP Rejection Notes'

    reject_reason = fields.Text(string='Alasan Reject', required=True)

    def cancel(self):
        return

    def ok(self):
        active_id = self.env.context.get('active_id')
        rkap_model = self.env['account.keuangan.rkap'].sudo()

        if active_id:
            rkap_id = rkap_model.browse([active_id])

            if rkap_id:
                rkap_id.write({
                    'approval_step': 1,
                    'state': 'rejected',
                })

                for x in rkap_id.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()

                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                self.env['rkap.approval.line'].create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f"Di-reject oleh {self.env.user.name} sebagai {level_val} dikarenakan: {self.reject_reason}.",
                    'rkap_id': rkap_id.id,
                })
                    
                for y in rkap_id.history_approval_ids.filtered(lambda y: 'Data RKAP telah di-submit' in y.note)[0]:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': 4,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.rkap')], limit=1).id,
                        'res_id': rkap_id.id,
                        'user_id': y.user_id.id,
                        'date_deadline': fields.Date.today() + timedelta(days=2),
                        'state': 'planned',
                        'status': 'todo',
                        'summary': """Harap segera merevisi nilai atau nominal RKAP setelah di-reject."""
                    })

        return {'type': 'ir.actions.act_window_close'}

class RejectWizardAGPNodin(models.TransientModel):
    _name = 'nodin.reject.wizard'
    _description = 'Nota Dinas Rejection Notes'

    reject_reason = fields.Text(string='Alasan Reject', required=True)

    def cancel(self):
        return

    def ok(self):
        active_id = self.env.context.get('active_id')
        nodin_model = self.env['account.keuangan.nota.dinas'].sudo()

        if active_id:
            nodin_id = nodin_model.browse([active_id])

            if nodin_id:
                for doc_line in nodin_id.document_ids:
                    doc_line.state = 'rejected'

                nodin_id.write({
                    'approval_step': 1,
                    'state': 'rejected',
                })

                for x in nodin_id.activity_ids.filtered(lambda x: x.status != 'approved'):
                    if x.user_id.id == self._uid:
                        x.status = 'approved'
                        x.action_done()

                level = self.env.user.level
                level_val = dict(self.env['res.users']._fields['level'].selection).get(level, level)
                self.env['nodin.approval.line'].create({
                    'user_id': self._uid,
                    'date': datetime.now(),
                    'note': f"Di-reject oleh {self.env.user.name} sebagai {level_val} dikarenakan: {self.reject_reason}.",
                    'nodin_id': nodin_id.id,
                })
                    
                for y in nodin_id.history_approval_ids.filtered(lambda y: 'Data Nota Dinas telah di-submit' in y.note)[0]:
                    self.env['mail.activity'].sudo().create({
                        'activity_type_id': 4,
                        'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'account.keuangan.nota.dinas')], limit=1).id,
                        'res_id': nodin_id.id,
                        'user_id': y.user_id.id,
                        'date_deadline': fields.Date.today() + timedelta(days=2),
                        'state': 'planned',
                        'status': 'todo',
                        'summary': """Harap segera merevisi nilai atau nominal Nota Dinas setelah di-reject."""
                    })

        return {'type': 'ir.actions.act_window_close'}
