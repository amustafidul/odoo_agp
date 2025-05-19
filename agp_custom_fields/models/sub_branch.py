from odoo import models, fields, api

from odoo import models, fields


class BranchInherit(models.Model):
    _inherit = 'res.branch'

    sub_branch_ids = fields.Many2many('sub.branch', string="Sub Branches")
    seq_id = fields.Integer(string="No Urut", required=True)
    code = fields.Char(string="Code", required=True)

    _sql_constraints = [
        ('seq_id_unik', 'UNIQUE(seq_id)', 'Sequence ID harus unik !')
    ]


class SubBranch(models.Model):
    _name = 'sub.branch'

    name = fields.Char(string="Sub Branch")
