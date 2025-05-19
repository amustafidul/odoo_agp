from odoo import api, fields, models


class ReportOvertimeWizard(models.TransientModel):
    _name = 'report.overtime.wizard'
    _description = 'Report Overtime Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    employee_ids = fields.Many2many('hr.employee', string="Employees")
    select_all_employees = fields.Boolean(string='Select All Employees')

    def action_generate_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'employee_ids': self.employee_ids.ids,
                'select_all_employees': self.select_all_employees
            },
        }
        return self.env.ref('agp_report_ib.action_report_overtime').report_action(self, data=data)