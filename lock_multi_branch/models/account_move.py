from odoo import models, fields, api, _
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    float_repr,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_fiscalyear_lock_date(self):
        for move in self:
            if move.branch_id:
                lock_branch_date = move.branch_id._get_user_fiscal_lock_date()
                print("="*50+"tes1"+"="*50)
                print(move.date)
                print(lock_branch_date)
                if move.date <= lock_branch_date:
                    print("="*50+"tes2"+"="*50)
                    if self.user_has_groups('account.group_account_manager'):
                        print("="*50+"tes3"+"="*50)
                        message = _("You cannot add/modify entries prior to and inclusive of the lock date %s.", format_date(self.env, lock_branch_date))
                    else:
                        print("="*50+"tes4"+"="*50)
                        message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role", format_date(self.env, lock_branch_date))
                    raise UserError(message)
            else:
                lock_date = move.company_id._get_user_fiscal_lock_date()
                if move.date <= lock_date:
                    if self.user_has_groups('account.group_account_manager'):
                        message = _("You cannot add/modify entries prior to and inclusive of the lock date %s.", format_date(self.env, lock_date))
                    else:
                        message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role", format_date(self.env, lock_date))
                    raise UserError(message)
        return True