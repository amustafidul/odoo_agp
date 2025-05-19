from odoo import models, fields, api

class JenisKegiatan(models.Model):
    _name = 'jenis.kegiatan'
    _description = 'Jenis Kegiatan'

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company')
    code = fields.Char(string="Code")