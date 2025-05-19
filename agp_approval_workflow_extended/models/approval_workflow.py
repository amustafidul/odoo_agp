from odoo import models, fields, api

class ApprovalWorkflowInheritDro(models.Model):
    _inherit = 'approval.workflow'

    total_approve = fields.Integer(string='Total Approval', compute='_compute_total_approve')
    branch_id = fields.Many2one('res.branch', string='Cabang')

    @api.depends('line_ids')
    def _compute_total_approve(self):
        for record in self:
            record.total_approve = len(record.line_ids)

class ApprovalWorkflowLineInheritDro(models.Model):
    _inherit = 'approval.workflow.line'

    eligible_user_id = fields.Many2one('res.users', string='User')
    level = fields.Selection([
        ('maker', 'Maker'),
        ('cabang', 'Approval Cabang'),
        ('usaha', 'Approval Usaha'),
        ('umum', 'Approval Umum & Admin'),
        ('anggaran', 'Approval Anggaran'),
        ('keuangan', 'Approval Keuangan'),
        ('bod', 'Approval BOD')
    ], string='Role Level')