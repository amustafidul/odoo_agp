from odoo import models, fields, api

class ApprovalWorkflowDocumentSetting(models.Model):
    _name = 'approval.workflow.document.setting'

    name = fields.Char(string='Name')
    model_id = fields.Many2one('ir.model', string='Menu')
    active = fields.Boolean(string='Active')
