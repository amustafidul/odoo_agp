from odoo import models, fields, api
from odoo.exceptions import ValidationError

class CashInOutWizard(models.TransientModel):
    _name = 'account.keuangan.cash.wizard'
    _description = 'Penagihan Wizard'

    payment_date = fields.Date(string="Tanggal Pembayaran", required=True)
    income_account = fields.Many2one('account.account', string="Rekening Pemasukan", required=True)
    payment_amount = fields.Float(string="Nominal Pembayaran", required=True)
    discount_amount = fields.Float(string="Nominal Potongan")
    discount_type = fields.Selection([
        ('fixed', 'Potongan Tetap'),
        ('percentage', 'Persentase Potongan')
    ], string="Jenis Potongan")

    keterangan = fields.Text(string='Keterangan', store=True)

    # Related tree fields
    line_ids = fields.One2many('account.keuangan.cash.line', 'cash_wizard_id', string="Detail Pembayaran")

    @api.onchange('discount_type', 'payment_amount')
    def _compute_discount_amount(self):
        """Contoh cara menghitung potongan secara otomatis berdasarkan tipe potongan."""
        if self.discount_type == 'percentage' and self.payment_amount:
            self.discount_amount = self.payment_amount * 0.10  # Misal 10% untuk contoh
        elif self.discount_type == 'fixed':
            self.discount_amount = 0.0  # Manual input
        
    def action_confirm(self):
        """Aksi ini akan dijalankan ketika pengguna menekan tombol 'Konfirmasi'."""
        if self.payment_amount <= 0:
            raise ValidationError("Nominal pembayaran harus lebih besar dari nol!")
        # Tambahkan logic lain jika diperlukan, seperti membuat pembayaran atau jurnal entry
        return {'type': 'ir.actions.act_window_close'}


class CashLine(models.TransientModel):
    _name = 'account.keuangan.cash.line'
    _description = 'Detail Cash In Out'

    cash_wizard_id = fields.Many2one('account.keuangan.cash.wizard', string="Wizard Cash In Out")
    description = fields.Char(string="Deskripsi")
    amount = fields.Float(string="Jumlah Pembayaran", required=True)
    account_id = fields.Many2one('account.account', string="Rekening Pembayaran", required=True)
