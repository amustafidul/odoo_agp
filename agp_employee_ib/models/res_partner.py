from odoo import models, fields, tools, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_alamat_domisili = fields.Text(string='Alamat Domisili')