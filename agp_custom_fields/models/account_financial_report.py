from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountFinancialReport(models.Model):
    _inherit = 'account.financial.report'

    name_eng = fields.Char(string="Report Name (en)")