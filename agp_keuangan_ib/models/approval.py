from odoo import models, fields, api

class Approval(models.Model):
    _name = 'account.keuangan.approval'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Approval for KKHC'

    kkhc_id = fields.Many2one('account.keuangan.kkhc', string="KKHC")
    name = fields.Char(related='kkhc_id.name', string="Nama KKHC", readonly=True)
    nama_anggaran = fields.Char(related='kkhc_id.nama_anggaran', string="Nama Anggaran", readonly=True)
    branch_id = fields.Many2one(related='kkhc_id.branch_id', string="Cabang", readonly=True)
    jumlah_ajuan_anggaran = fields.Float(related='kkhc_id.jumlah_ajuan_anggaran', string="Jumlah Ajuan", readonly=True)
    jumlah_pemasukan_disetujui = fields.Float(string="Jumlah Pemasukan Disetujui")
    jumlah_pengeluaran_disetujui = fields.Float(string="Jumlah Pengeluaran Disetujui")
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='draft', string="Status")


    rkap_id = fields.Many2one('account.keuangan.rkap', string="RKAP")
    name = fields.Char(related='rkap_id.name', string="Nama KKHC", readonly=True)
    branch_id = fields.Many2one(related='rkap_id.branch_id', string="Cabang", readonly=True)


    @api.model
    def approve(self):
        self.state = 'approved'

    @api.model
    def reject(self):
        self.state = 'rejected'

    