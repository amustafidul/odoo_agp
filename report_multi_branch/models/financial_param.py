from odoo import models, fields, api
from odoo.exceptions import UserError
import ast

class FinancialParam(models.Model):
    _name = 'financial.param'
    _description = "Financial Param"

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company')
    sub_param_ids = fields.One2many('financial.param.line', 'param_id', string='Line')


class FinancialParamLine(models.Model):
    _name = 'financial.param.line'
    _description = "Financial Param Line"
    _order = "sequence"

    name = fields.Char(string='Name')
    name_eng = fields.Char(string='Name English')
    sequence = fields.Integer(string='Sequence', index=True)
    param_id = fields.Many2one('financial.param', string='Param')
    code = fields.Char(string='Code')
    type = fields.Selection([
        ('account', 'Account'),
        ('formula', 'Formula')
    ], string='Value Type')
    formula = fields.Char(string='Formula')
    account_ids = fields.Many2many(comodel_name='account.account', relation='financial_param_line_account_rel', string='Account')
    level = fields.Integer(string='Level')
    bold = fields.Boolean(string='Bold', default=False)
    invisible = fields.Boolean(string='Invisible', default=False)
    blank = fields.Boolean(string='Blank', default=False)
    balance = fields.Float(string='Balance')
    balance1 = fields.Float(string='Balance1')
    balance2 = fields.Float(string='Balance2')