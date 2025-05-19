from odoo import models, fields, api


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    relasi = fields.Many2one(comodel_name='res.partner', string='Relasi')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')

    show_bank_account = fields.Boolean(compute='_compute_show_bank_account', store=True)

    @api.depends('journal_id')
    def _compute_show_bank_account(self):
        for record in self:
            print(f"Computing show_bank_account for journal {record.journal_id.name}")
            record.show_bank_account = record.journal_id.name in ['Bukti Kas Masuk', 'Bukti Kas Keluar', 'Penerimaan Pelunasan']

    @api.onchange('bank_account_id')
    def _onchange_bank_account_id(self):
        if self.bank_account_id:
            account_id = self.bank_account_id.account_id.id if self.bank_account_id.account_id else False
            self.account_id = account_id
