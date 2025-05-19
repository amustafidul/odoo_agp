from odoo import models, fields, _
from odoo.exceptions import UserError, AccessError

class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"

    def validate_move(self):
        user = self.env.user
        if not user.has_group('base.group_system') and not user.has_group('module_name.group_advisor') and not user.allow_posting_journal_entries:
            raise AccessError(_('Kesalahan Hak Akses: \n'
                                 'Operasi yang diminta tidak dapat diselesaikan karena hak akses. \n'
                                 'Silakan hubungi administrator.\n '
                                'Fitur ini hanya diizinkan untuk grup pengguna:\n '
                                '- Allow Confirm / Posting Journal Entries'))

        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
        elif self._context.get('active_model') == 'account.journal':
            domain = [('journal_id', '=', self._context.get('active_id')), ('state', '=', 'draft')]
        else:
            raise UserError(_("Missing 'active_model' in context."))

        moves = self.env['account.move'].search(domain).filtered('line_ids')
        if not moves:
            raise UserError(_('There are no journal items in the draft state to post.'))
        if self.force_post:
            moves.auto_post = 'no'
        moves._post(not self.force_post)
        return {'type': 'ir.actions.act_window_close'}
