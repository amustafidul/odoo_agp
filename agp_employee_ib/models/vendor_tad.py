from odoo import models, fields, api


class VendorTAD(models.Model):
    _name = 'agp.vendor.tad'
    _description = 'Master data vendor (TAD)'

    name = fields.Char(string="Vendor", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)