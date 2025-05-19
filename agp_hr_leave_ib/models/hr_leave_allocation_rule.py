from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrLeaveAllocationRule(models.Model):
    _name = 'hr.leave.allocation.rule'
    _description = 'Leave Allocation Rules'

    name = fields.Char(string='Rule Name', compute='_compute_name')
    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type', required=True, domain=[('requires_allocation','=','yes')])
    number_of_days = fields.Integer(string='Number of Days', required=True)

    @api.constrains('number_of_days')
    def _check_number_of_days(self):
        for record in self:
            if record.number_of_days <= 0:
                raise ValidationError("The number of days must be greater than 0.")

    @api.depends('leave_type_id')
    def _compute_name(self):
        self.name = 'New Rules'
        for rec in self:
            rec.name = rec.leave_type_id.name + ' Rules' if rec.leave_type_id else 'New Rules'