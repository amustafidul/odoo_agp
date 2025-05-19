from odoo import models, fields, api


class AccountAccount(models.Model):
    _inherit = 'account.account'

    name_eng = fields.Char(string="Account Name (en)")
