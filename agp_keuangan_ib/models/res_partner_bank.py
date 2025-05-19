from odoo import fields, models

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'


    phone = fields.Char(string="Contact Person (Phone)")
    email = fields.Char(string="Contact Person (Email)")
    cabang_pembuka = fields.Char(string="Cabang Pembuka")

    journal_id = fields.Many2one('account.journal', string="Journal")




