from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = 'res.company'

    round_tax = fields.Selection([
        ('NONE','NONE'),
        ('UP','UP'),
        ('DOWN','DOWN'),
        ('HALF-UP','HALF-UP'),
    ], string='Round Tax')
    precision_rounding = fields.Float(string='Precision Rounding', default=1)