from odoo import models, fields, api, _
from datetime import date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def create_yearly_leave_allocations(self):
        today = date.today()
        current_year = today.year

        allocation_rules = self.env['hr.leave.allocation.rule'].search([])
        leave_type_ids = allocation_rules.mapped('leave_type_id').ids

        employees = self.env['hr.employee'].search([])

        chunk_size = 100
        for offset in range(0, len(employees.ids), chunk_size):
            employee_ids_chunk = employees.ids[offset:offset + chunk_size]
            employees_chunk = self.env['hr.employee'].browse(employee_ids_chunk)
            employees_chunk.read(['employment_type', 'histori_jabatan_ids'])

            allocations_group = self.env['hr.leave.allocation'].read_group(
                [
                    ('employee_id', 'in', employee_ids_chunk),
                    ('holiday_status_id', 'in', leave_type_ids),
                    ('date_from', '>=', f'{current_year}-01-01'),
                    ('date_to', '<=', f'{current_year}-12-31'),
                ],
                ['employee_id', 'holiday_status_id'],
                ['employee_id', 'holiday_status_id']
            )
            # Mapping: (employee_id, leave_type_id) -> count
            allocation_counts = {
                (group['employee_id'][0], group['holiday_status_id'][0]): group['__count']
                for group in allocations_group
            }

            for employee in employees_chunk:
                tmt_date = employee.histori_jabatan_ids.sorted('id', reverse=True)[:1].tmt_date \
                    if employee.histori_jabatan_ids else None

                if not tmt_date:
                    continue

                for rule in allocation_rules:
                    leave_type = rule.leave_type_id

                    if allocation_counts.get((employee.id, leave_type.id), 0):
                        continue

                    if leave_type.name == "Cuti Tahunan":
                        if employee.employment_type == 'TAD' and today < tmt_date + relativedelta(years=1):
                            continue
                        elif tmt_date.year == current_year:
                            months_remaining = 12 - tmt_date.month
                            days_allocation = (rule.number_of_days / 12) * months_remaining
                        else:
                            days_allocation = rule.number_of_days
                    else:
                        days_allocation = rule.number_of_days

                    allocation_vals = {
                        'name': f'{leave_type.name} Allocation {current_year}',
                        'employee_id': employee.id,
                        'holiday_status_id': leave_type.id,
                        'number_of_days': days_allocation,
                        'date_from': f'{current_year}-01-01',
                        'date_to': f'{current_year}-12-31',
                        'state': 'draft',
                    }
                    allocation = self.create(allocation_vals)
                    allocation.action_validate()

            self._cr.commit()

    @api.model
    def reset_leave_allocations(self):
        today = date.today()
        current_year = today.year
        leave_allocations = self.env['hr.leave.allocation'].search([
            ('date_to', '<', f'{current_year}-01-01')
        ])

        if leave_allocations:
            leave_allocations.action_refuse()
            leave_allocations.action_draft()
            leave_allocations.unlink()

        self.create_yearly_leave_allocations()