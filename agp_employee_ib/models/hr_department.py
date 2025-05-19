from odoo import models, fields, api, _


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    branch_id = fields.Many2one('hr.branch', required=True)