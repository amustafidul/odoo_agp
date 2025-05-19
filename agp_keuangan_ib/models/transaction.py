from odoo import models, fields, api

class AccountKeuanganTransaction(models.Model):
    _name = 'account.keuangan.transaction'
    _description = 'Transaction for Payments'

    payment_id = fields.Many2one('account.keuangan.register.payment', string="Payment Reference")
    invoice_id = fields.Many2one('account.keuangan.invoice', string="Invoice", related="payment_id.invoice_id", store=True)
    bank_account_id = fields.Many2one('res.partner.bank', string="Bank Account", related="payment_id.bank_account_id", store=True)
    amount_paid = fields.Float(string="Amount Paid", related="payment_id.amount_paid", store=True)
    payment_date = fields.Date(string="Payment Date", related="payment_id.payment_date", store=True)
    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string="Jenis Kegiatan", related="payment_id.jenis_kegiatan_id", readonly=True, store=True)
    account_code_id = fields.Many2one('account.account', string="Account Code", related="payment_id.account_code_id", readonly=True, store=True)
    kode_anggaran = fields.Char(string="Kode Anggaran", related="payment_id.kode_anggaran", readonly=True, store=True)
    nodin_line_id = fields.Many2one('account.keuangan.monitor.kkhc.line', string="Nota Dinas Line")
    transaction_branch_id = fields.Many2one('res.branch', related='invoice_id.branch_id')

    @api.model
    def fetch_transactions(self, invoice_id):
    
        self.env.cr.execute("""
            SELECT id, bank_account_id, invoice_id, amount_paid, payment_date
            FROM account_keuangan_register_payment
            WHERE invoice_id = %s
        """, (invoice_id,))
        payments = self.env.cr.dictfetchall()

        for payment in payments:
            self.create({
                'payment_id': payment['id'],
            })