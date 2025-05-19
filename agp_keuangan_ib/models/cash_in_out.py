from odoo import models, fields, api, _

class CashInOut(models.Model):
    _name = 'account.keuangan.transaction'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Cash In and Cash Out'

    name = fields.Char(string="Name", required=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    
    # Bank account field in CashInOut model
    bank_account_id = fields.Many2one('res.partner.bank', string="Bank Account", required=True)

    # Computed field to calculate total paid per bank account
    total_paid = fields.Float(string="Total Paid", compute="_compute_total_paid", store=True)

    @api.depends('bank_account_id')
    def _compute_total_paid(self):
        for record in self:
            # Calculate total paid from account.keuangan.register.payment for the given bank_account_id
            payments = self.env['account.keuangan.register.payment'].search([
                ('bank_account_id', '=', record.bank_account_id.id)
            ])
            record.total_paid = sum(payments.mapped('amount_paid'))