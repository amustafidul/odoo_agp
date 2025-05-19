from odoo import models, fields, api, _


class DinasKomponen(models.Model):
    _name = 'dinas.komponen'
    _description = 'Master Komponen Biaya Dinas'

    name = fields.Char(string="Nama Komponen", required=True)
    is_laundry = fields.Boolean(string="Apakah Biaya Cuci / Laundry?", default=False)