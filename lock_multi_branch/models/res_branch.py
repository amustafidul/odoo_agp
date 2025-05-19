from datetime import timedelta, datetime, date

from odoo import models, fields, api, _

class ResBranch(models.Model):
    _inherit = 'res.branch'

    period_lock_date = fields.Date(
        string="Journals Entries Lock Date",
        tracking=True,
        help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this"
             " date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(
        string="All Users Lock Date",
        tracking=True,
        help="No users, including Advisers, can edit accounts prior to and inclusive of this date."
             " Use it for fiscal year locking for example.")
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        tracking=True,
        help="No users can edit journal entries related to a tax prior and inclusive of this date.")

    
    def _get_user_fiscal_lock_date(self):
        """Get the fiscal lock date for this branch depending on the user"""
        if not self:
            return date.min
        self.ensure_one()
        lock_date = max(self.period_lock_date or date.min, self.fiscalyear_lock_date or date.min)
        if self.user_has_groups('account.group_account_manager'):
            lock_date = self.fiscalyear_lock_date or date.min
        return lock_date