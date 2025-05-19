from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    rk_bank_account = fields.Selection([("rk","R/K"),("bank_account","Bank Account")], string='R/K or Bank Account')
    rk_account_id = fields.Many2one('account.account', string='R/K')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account')

   
    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        if self.rk_bank_account == 'rk':
            vals.update({'rk_bank_account_id': self.rk_account_id.id})
        elif self.rk_bank_account == 'bank_account':
            vals.update({'rk_bank_account_id': self.bank_account_id.account_id.id})
        return vals

    
    @api.depends('payment_type', 'company_id', 'can_edit_wizard', 'bank_account_id')
    def _compute_available_journal_ids(self):
        for wizard in self:
            if wizard.bank_account_id:
                # Ambil journal_id dari bank_account_id yang dipilih
                wizard.available_journal_ids = wizard.bank_account_id.journal_id
            elif wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
                wizard.available_journal_ids = wizard._get_batch_available_journals(batch)
            else:
                wizard.available_journal_ids = self.env['account.journal'].search([
                    ('company_id', '=', wizard.company_id.id),
                    ('type', 'in', ('bank', 'cash')),
                ])
                

    @api.depends('available_journal_ids', 'bank_account_id')
    def _compute_journal_id(self):
        for wizard in self:
            if wizard.bank_account_id and wizard.bank_account_id.journal_id:
                # Ambil journal_id dari bank_account_id yang dipilih
                wizard.journal_id = wizard.bank_account_id.journal_id
            elif wizard.can_edit_wizard:
                batch = wizard._get_batches()[0]
                wizard.journal_id = wizard._get_batch_journal(batch)
            else:
                wizard.journal_id = self.env['account.journal'].search([
                    ('type', 'in', ('bank', 'cash')),
                    ('company_id', '=', wizard.company_id.id),
                    ('id', 'in', self.available_journal_ids.ids)
                ], limit=1)
