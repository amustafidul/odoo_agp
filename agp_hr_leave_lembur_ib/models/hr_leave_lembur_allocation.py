from odoo import models, fields, api


class HrLeaveLemburAllocation(models.Model):
    _name = 'hr.leave.lembur.allocation'
    _inherit = 'hr.leave.allocation'
    _description = 'Alokasi Lembur'

    def _default_lembur_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', 'yes')]
        else:
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', 'yes'), ('employee_requests', '=', 'yes')]
        return self.env['hr.leave.type.lembur'].search(domain, limit=1)

    def _domain_lembur_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            return [('requires_allocation', '=', 'yes')]
        return [('employee_requests', '=', 'yes')]

    lembur_status_id = fields.Many2one(
        "hr.leave.type.lembur", compute='_compute_lembur_status_id', store=True, string="Tipe Lembur", required=True,
        readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)],
                'validate': [('readonly', True)]},
        domain=_domain_lembur_status_id,
        default=_default_lembur_status_id)

    @api.depends('accrual_plan_id')
    def _compute_lembur_status_id(self):
        default_lembur_status_id = None
        for lembur in self:
            if not lembur.lembur_status_id:
                if lembur.accrual_plan_id:
                    lembur.lembur_status_id = lembur.accrual_plan_id.time_off_type_id
                else:
                    if not default_lembur_status_id:  # fetch when we need it
                        default_lembur_status_id = self._default_lembur_status_id()
                    lembur.lembur_status_id = default_lembur_status_id