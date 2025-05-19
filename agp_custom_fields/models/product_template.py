from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    account_piutang_id = fields.Many2one('account.account', domain=[('account_type', 'in', ['asset_receivable', 'liability_payable'])], string='Akun Piutang')
    account_hutang_id = fields.Many2one('account.account', domain=[('account_type', 'in', ['asset_receivable', 'liability_payable'])], string='Akun Hutang')