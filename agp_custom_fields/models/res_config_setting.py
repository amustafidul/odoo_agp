from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    round_tax = fields.Selection([
        ('NONE','NONE'),
        ('UP','UP'),
        ('DOWN','DOWN'),
        ('HALF-UP','HALF-UP'),
    ], string='Round Tax', related='company_id.round_tax', readonly=False)
    precision_rounding = fields.Float(string='Precision Rounding', related='company_id.precision_rounding', readonly=False)