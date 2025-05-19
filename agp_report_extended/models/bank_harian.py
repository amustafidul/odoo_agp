from odoo import fields, models

class BankHarian(models.Model):
    _inherit = 'account.keuangan.bank.harian'

    catatan_bank_harian = fields.Text(string='Catatan')
    sisa_saldo = fields.Float(string='Sisa Saldo Catatan')
    note_line_ids = fields.One2many('account.keuangan.bank.harian.notes', 'bank_harian_id', string='Catatan Lines')

class BankHarianNoteLines(models.Model):
    _name = 'account.keuangan.bank.harian.notes'
    _description = 'Catatan Bank Harian'

    bank_harian_id = fields.Many2one('account.keuangan.bank.harian', string='Bank Harian')
    no = fields.Integer(string="No", compute="_compute_no")
    ket_satu = fields.Char(string='Keterangan', default='')
    saldo_satu = fields.Float(string='Saldo')
    ket_dua = fields.Char(string='Keterangan', default='')
    saldo_dua = fields.Float(string='Saldo')

    def _compute_no(self):
        for index, record in enumerate(self, start=1):
            record.no = index