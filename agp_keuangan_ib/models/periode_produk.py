from odoo import models, fields, api, _

class PeriodeProduk(models.Model):
    _name = 'account.keuangan.periode.produk'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Periode Produk'

    name = fields.Char(string='Periode Produk', required=True)