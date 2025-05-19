from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_posting_journal_entries = fields.Boolean(string='Allow Confirm / Posting Journal Entries', default=False)
