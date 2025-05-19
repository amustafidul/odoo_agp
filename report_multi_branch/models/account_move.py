from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    relasi = fields.Many2one(comodel_name='res.partner', string='Relasi')
    no_faktur = fields.Char(string='No Faktur')
    show_bank_account = fields.Boolean(compute='_compute_show_bank_account', store=True)
    show_relasi = fields.Boolean(compute='_compute_show_relasi', store=True)


    @api.depends('journal_id')
    def _compute_show_relasi(self):
        for record in self:
            record.show_relasi = record.journal_id.name == 'Jurnal Umum'
    
    @api.model
    def create(self, vals):
        # Ensure show_bank_account is set correctly when creating a new record
        if 'journal_id' in vals:
            journal = self.env['account.journal'].browse(vals['journal_id'])
            vals['show_bank_account'] = journal.name in ['Bukti Kas Masuk', 'Bukti Kas Keluar']
        return super(AccountMove, self).create(vals)

    @api.depends('journal_id')
    def _compute_show_bank_account(self):
        for record in self:
            record.show_bank_account = record.journal_id.name in ['Bukti Kas Masuk', 'Bukti Kas Keluar']

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            print(f"Journal selected: {self.journal_id.name}")
            self.show_bank_account = self.journal_id.name in ['Bukti Kas Masuk', 'Bukti Kas Keluar']
        else:
            print("No journal selected")
            self.show_bank_account = False