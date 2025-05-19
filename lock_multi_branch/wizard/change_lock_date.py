from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ChangeLockDate(models.TransientModel):
    _inherit = 'change.lock.date'

    branch_ids = fields.Many2many(comodel_name='res.branch', relation='lock_date_branch_rel', string='Branch')

    def update_lock_date(self):
        self.ensure_one()
        if self.branch_ids:
            for branch in self.branch_ids:
                branch.write({
                    'period_lock_date': self.period_lock_date,
                    'fiscalyear_lock_date': self.fiscalyear_lock_date,
                    'tax_lock_date': self.tax_lock_date,
                })
        else:
            has_manager_group = self.env.user.has_group('account.group_account_manager')
            if not (has_manager_group or self.env.uid == SUPERUSER_ID):
                raise UserError(_("You Are Not Allowed To Perform This Operation"))
            self.company_id.sudo().write({
                'period_lock_date': self.period_lock_date,
                'fiscalyear_lock_date': self.fiscalyear_lock_date,
                'tax_lock_date': self.tax_lock_date,
            })