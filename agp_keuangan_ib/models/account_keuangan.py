from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class AccountKeuangan(models.Model):
    _name = "account.keuangan"
    _inherits = {'account.move': 'move_id', 'account.move.line': 'move_line_id'}
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, tracking=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('account.keuangan') or '/')
    move_id = fields.Many2one(comodel_name='account.move', ondelete='cascade',tracking=True,)
    move_line_id = fields.Many2one(comodel_name='account.move.line', ondelete='cascade', tracking=True,)
    # example_field = fields.Char(string="Example Field")
    # example_field1 = fields.Many2one('res.users', 'User')

    def action_post(self):
        # Panggil method action_post dari model account.move
        return self.move_id.action_post()

    made_sequence_hole = fields.Boolean(compute='move_id._compute_made_sequence_hole')