from odoo import fields, models

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    account_id = fields.Many2one('account.account', string='Bank Account')


class ResBank(models.Model):
    _inherit = 'res.bank'

    account_id = fields.Many2one('account.account', string='Bank Account')