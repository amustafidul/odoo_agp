from odoo import models, fields, api


class DirjenPajak(models.Model):
    _name = 'dirjen.pajak'
    _description = 'Dirjen Pajak'

    name = fields.Char(string='NOMOR EFAKTUR')
    no_npwp = fields.Char(string='NPWP PT')
    nama_pt = fields.Char(string='NAMA PT')
    date = fields.Date(string='Date')
    bulan = fields.Integer(string='BULAN')
    tahun = fields.Char(string='TAHUN')
    nominal_invoice = fields.Float(string='NOMINAL DPP')
    nominal_ppn = fields.Float(string='NOMINAL PPN')
    no_invoice_odoo = fields.Char(string='NO INVOICE DARI ODOO')
    created_by = fields.Many2one('res.users', string='Created By', readonly=True, default=lambda self: self.env.user)
    created_date = fields.Datetime(string='Created Date', readonly=True, default=fields.Datetime.now)
    