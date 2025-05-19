from odoo import models, fields, api, _


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    leave_validation_type = fields.Selection(selection_add=[('dynamic_approval', 'Dynamic Approval')])
    sick_time_off = fields.Boolean('Sick Time Off')