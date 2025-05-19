from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta


class WizardCreateMassPayslip(models.TransientModel):
    _name = 'wizard.create.mass.payslip'
    _description = 'Wizard for Mass Payslip Creation'

    date_from = fields.Date(string="Date From", required=True)
    date_to = fields.Date(string="Date To", required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    select_all = fields.Boolean('Select All Employees')

    def action_create_payslips(self):
        employees = self.employee_ids
        if self.select_all:
            employees = self.env['hr.employee'].search([])

        if not employees:
            raise ValidationError("No employees selected.")

        for emp in employees:
            for date_from, date_to in self._get_periods(emp):
                payslip_vals = {
                    'employee_id': emp.id,
                    'date_from': date_from,
                    'date_to': date_to,
                }

                dummy = self.env['hr.payslip'].new(payslip_vals)
                dummy.onchange_employee()
                final_vals = dummy._convert_to_write(dummy._cache)

                payslip = self.env['hr.payslip'].create(final_vals)
                payslip.compute_sheet()
                payslip.action_payslip_done()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Employee Payslips',
            'view_mode': 'tree,form',
            'res_model': 'hr.payslip',
            'target': 'current',
        }

    def _get_periods(self, employee):
        contract = employee.contract_id
        if not contract:
            return [(self.date_from, self.date_to)]

        dummy = self.env['hr.payslip'].new({
            'employee_id': employee.id,
            'contract_id': contract.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
        })

        dummy.onchange_employee()
        payslip = dummy

        is_prorated, split_date = payslip.is_prorated()
        if is_prorated and split_date and self.date_from < split_date < self.date_to:
            return [
                (self.date_from, split_date - timedelta(days=1)),
                (split_date, self.date_to)
            ]
        return [(self.date_from, self.date_to)]