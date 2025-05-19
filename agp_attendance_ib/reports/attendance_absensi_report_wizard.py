from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Wizard for Attendance Report'

    date_from = fields.Date(string="Tanggal Check In", required=True)
    date_to = fields.Date(string="Tanggal Check Out", required=True)
    employee_ids = fields.Many2many('hr.employee', string="Karyawan")
    all_employee = fields.Boolean(string="Semua Karyawan", default=False)

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        invalid_records = self.filtered(lambda r: r.date_from > r.date_to)
        if invalid_records:
            raise ValidationError(_("Tanggal mulai tidak boleh lebih besar dari tanggal selesai."))

    def print_report(self):
        if self.all_employee:
            employee_ids = self.env['hr.employee'].search([]).mapped('id')
        else:
            employee_ids = self.employee_ids.mapped('id')

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_ids': employee_ids,
        }
        return self.env.ref('agp_attendance_ib.attendance_excel_report_action').report_action(self, data=data)

    def print_report_pdf(self):
        if self.all_employee:
            employee_ids = self.env['hr.employee'].search([]).mapped('id')
        else:
            employee_ids = self.employee_ids.mapped('id')

        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_ids': employee_ids,
        }

        return self.env.ref('agp_attendance_ib.action_report_attendance_absensi_pdf').report_action(self, data=data)