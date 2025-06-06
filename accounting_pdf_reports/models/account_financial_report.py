# -*- coding: utf-8 -*-

from odoo import api, models, fields


class AccountFinancialReport(models.Model):
    _name = "account.financial.report"
    _order = 'sequence, id'
    _description = "Account Report"

    @api.depends('parent_id', 'parent_id.level')
    def _get_level(self):
        '''Returns a dictionary with key=the ID of a record and value = the level of this
           record in the tree structure.'''
        for report in self:
            level = 0
            if report.parent_id:
                level = report.parent_id.level + 1
            report.level = level

    def _get_children_by_order(self):
        '''returns a recordset of all the children computed recursively, and sorted by sequence. Ready for the printing'''
        res = self
        children = self.search([('parent_id', 'in', self.ids)], order='sequence ASC')
        if children:
            for child in children:
                res += child._get_children_by_order()
        return res

    name = fields.Char('Report Name', required=True, translate=True)
    parent_id = fields.Many2one('account.financial.report', 'Parent')
    children_ids = fields.One2many('account.financial.report', 'parent_id', 'Account Report')
    sequence = fields.Integer('Sequence')
    level = fields.Integer(compute='_get_level', string='Level', store=True, recursive=True)
    type = fields.Selection([
        ('sum', 'View'),
        ('accounts', 'Accounts'),
        ('multi_accounts', 'Multi Accounts'),
        ('account_type', 'Account Type'),
        ('account_report', 'Report Value'),
        ], 'Type', default='sum')
    account_ids = fields.Many2many('account.account', 'account_account_financial_report',
                                   'report_line_id', 'account_id', 'Accounts')
    multi_account_ids = fields.One2many('multi.accounts.financial.report', 'financial_id', string='Multi Account')
    account_report_id = fields.Many2one('account.financial.report', 'Report Value')
    account_type_ids = fields.Many2many('account.account.type', 'account_account_financial_report_type',
                                        'report_id', 'account_type_id', 'Account Types')
    report_domain = fields.Char(string="Report Domain")
    sign = fields.Selection([('-1', 'Reverse balance sign'), ('1', 'Preserve balance sign')], 'Sign on Reports',
                            required=True, default='1',
                            help='For accounts that are typically more debited than credited and that you would'
                                 ' like to print as negative amounts in your reports, you should reverse the sign'
                                 ' of the balance; e.g.: Expense account. The same applies for accounts that are '
                                 'typically more credited than debited and that you would like to print as positive '
                                 'amounts in your reports; e.g.: Income account.')
    display_detail = fields.Selection([
        ('no_detail', 'No detail'),
        ('detail_flat', 'Display children flat'),
        ('detail_with_hierarchy', 'Display children with hierarchy')
        ], 'Display details', default='detail_flat')
    style_overwrite = fields.Selection([
        ('0', 'Automatic formatting'),
        ('1', 'Main Title 1 (bold, underlined)'),
        ('2', 'Title 2 (bold)'),
        ('3', 'Title 3 (bold, smaller)'),
        ('4', 'Normal Text'),
        ('5', 'Italic Text (smaller)'),
        ('6', 'Smallest Text'),
        ], 'Financial Report Style', default='0',
        help="You can set up here the format you want this record to be displayed. "
             "If you leave the automatic formatting, it will be computed based on the "
             "financial reports hierarchy (auto-computed field 'level').")
    children_ids = fields.One2many('account.financial.report', 'parent_id', string='Children')



class MultiAccountsFinancialReport(models.Model):
    _name = "multi.accounts.financial.report"
    _description = "Multi Account Report"

    name = fields.Char(string='Name')
    name_eng = fields.Char(string="Name (en)")
    financial_id = fields.Many2one('account.financial.report', string='Financial Report')
    account_ids = fields.Many2many('account.account', 'account_multi_accounts_fr', 'multi_account_id', 'account_id', 'Accounts')