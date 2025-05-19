import datetime
from odoo import models, fields, api


class HrLeaveTypeLembur(models.Model):
    _name = 'hr.leave.type.lembur'
    _inherit = 'hr.leave.type'
    _description = 'Tipe Lembur'

    allocation_lembur_count = fields.Integer(
        compute='_compute_allocation_lembur_count', string='Allocations')

    group_days_leave_lembur = fields.Float(
        compute='_compute_group_days_leave_lembur', string='Group Lembur')

    def _compute_allocation_lembur_count(self):
        for allocation in self:
            allocation.allocation_lembur_count = 0

    def action_see_group_leaves_lembur(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("agp_hr_leave_lembur_ib.hr_leave_lembur_action_new_request")
        action['context'] = {
            'search_default_need_approval_approved': 1,
            'search_default_this_year': 1,
        }
        return action

    def _compute_group_days_leave_lembur(self):
        min_datetime = fields.Datetime.to_string(datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
        max_datetime = fields.Datetime.to_string(datetime.datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59))
        domain = [
            ('lembur_status_id', 'in', self.ids),
            ('date_from', '>=', min_datetime),
            ('date_from', '<=', max_datetime),
            ('state', 'in', ('validate', 'validate1', 'confirm')),
        ]
        grouped_res = self.env['hr.leave.lembur']._read_group(
            domain,
            ['lembur_status_id'],
            ['lembur_status_id'],
        )
        grouped_dict = dict((data['lembur_status_id'][0], data['lembur_status_id_count']) for data in grouped_res)
        for allocation in self:
            allocation.group_days_leave_lembur = grouped_dict.get(allocation.id, 0)

    leave_validation_type = fields.Selection(selection='_compute_dynamic_leave_validation_type_selection', default='hr', string='Leave Validation')

    def _compute_dynamic_leave_validation_type_selection(self):
        if self.env.context.get('default_hr_leave_lembur') == 1:
            return [
                ('no_validation', 'No Validation'),
                ('hr', 'By Lembur Officer'),
                ('manager', "By Employee's Approver"),
                ('both', "By Employee's Approver and Lembur Officer"),
                ('dynamic_approval', "Dynamic Approval")]
        else:
            return [
                ('no_validation', 'No Validation'),
                ('hr', 'By Time Off Officer'),
                ('manager', "By Employee's Approver"),
                ('both', "By Employee's Approver and Time Off Officer"),
                ('dynamic_approval', "Dynamic Approval")]

    allocation_validation_type = fields.Selection(selection='_compute_dynamic_allocation_validation_type_selection', default='no', string='Approval',
        compute='_compute_allocation_validation_type', store=True, readonly=False,
        help="""Select the level of approval needed in case of request by employee
            - No validation needed: The employee's request is automatically approved.
            - Approved by Time Off Officer: The employee's request need to be manually approved by the Time Off Officer.""")

    def _compute_dynamic_allocation_validation_type_selection(self):
        if self.env.context.get('default_hr_leave_lembur') == 1:
            return [
                    ('officer', 'Approved by Lembur Officer'),
                    ('no', 'No validation needed')]
        else:
            return [
                    ('officer', 'Approved by Time Off Officer'),
                    ('no', 'No validation needed')]