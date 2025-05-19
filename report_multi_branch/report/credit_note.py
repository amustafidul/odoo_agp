from odoo import api, models, fields, _
from odoo.exceptions import UserError
from datetime import datetime


class CreditNote(models.Model):
    _name = 'report.report_multi_branch.credit_note'
    _description = 'Credit Note'

    name = fields.Char(string='Report Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    branch_id = fields.Many2one('res.branch', string='Dari', required=True, default=lambda self: self.env.user.branch_id.id, readonly=True)
    branch_code = fields.Char(related='branch_id.code', string='Branch Code', store=True, readonly=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    perihal = fields.Char(string='Perihal', required=True)
    to = fields.Char(string='Untuk', required=True)
    lampiran = fields.Char(string='Lampiran', optional=True)
    note = fields.Html(string='Deskripsi', translate=True)
    account_line_ids = fields.One2many('report.credit_note.line', 'credit_note_id', string='Account Lines')
    total_amount = fields.Float(string='Total Amount', compute='_compute_totals', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    total_debit = fields.Float(string='Total Debit', compute='_compute_totals', store=True)
    total_credit = fields.Float(string='Total Credit', compute='_compute_totals', store=True)


    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        branch_id = self.env.user.branch_id.id
        args.append(('branch_id', '=', branch_id))
        return super(CreditNote, self).search(args, offset, limit, order, count)

    @api.depends('account_line_ids.debit', 'account_line_ids.credit')
    def _compute_totals(self):
        for record in self:
            total_debit = sum(line.debit for line in record.account_line_ids)
            total_credit = sum(line.credit for line in record.account_line_ids)
            record.total_debit = total_debit
            record.total_credit = total_credit

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('New')) == _('New'):            
    #         # Get the date details
    #         date_str = vals.get('date', fields.Date.context_today(self))
    #         date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
    #         year = date_obj.strftime('%Y')
    #         month = int(date_obj.strftime('%m'))
    #         roman_month = self._to_roman(month)
            
    #         # Get the default branch of the user
    #         user = self.env.user
    #         default_branch = user.branch_id[0] if user.branch_id else None
    #         branch_code = default_branch.code if default_branch else 'KOSONG'
            
    #         # Generate the custom sequence number
    #         sequence_code = self.env['ir.sequence'].next_by_code('report.credit_note') or '0000'

    #         # Generate the custom sequence
    #         vals['name'] = f'{sequence_code}/CN-{branch_code}/{roman_month}/{year}'
        
    #     return super(CreditNote, self).create(vals)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):            
            # Get the date details
            date_str = vals.get('date', fields.Date.context_today(self))
            date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
            year = date_obj.strftime('%Y')
            month = int(date_obj.strftime('%m'))
            roman_month = self._to_roman(month)
            
            # Get the default branch of the user
            user = self.env.user
            default_branch = user.branch_id[0] if user.branch_id else None
            branch_code = default_branch.code if default_branch else 'KOSONG'
            
            # Get the department code of the user
            department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
            # Generate the custom sequence number
            sequence_code = self.env['ir.sequence'].next_by_code('report.spp') or '0000'

            # Generate the custom sequence
            vals['name'] = f'CN{sequence_code}/{department_code}/{branch_code}/{roman_month}/{year}'
        
        return super(CreditNote, self).create(vals)


    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')

    def print_credit_note(self):
        return self.env.ref('report_multi_branch.report_credit_note').report_action(self)

    def action_duplicate(self):
        new_record = self.copy()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': new_record.id,
            'target': 'current',
        }

class CreditNoteLine(models.Model):
    _name = 'report.credit_note.line'
    _description = 'Credit Note Line'

    credit_note_id = fields.Many2one('report.report_multi_branch.credit_note', string='Credit Note Reference', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', required=True)
    amount = fields.Float(string='Amount', required=True)
    debit = fields.Float(string='Debit', required=True)
    credit = fields.Float(string='Credit', required=True)
