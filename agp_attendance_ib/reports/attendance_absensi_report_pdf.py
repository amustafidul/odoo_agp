from odoo import models, api, fields
from datetime import timedelta


class AttendancePDFReport(models.AbstractModel):
    _name = 'report.agp_attendance_ib.attendance_absensi_report_pdf'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Attendance PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = fields.Date.from_string(data.get('date_from'))
        date_to = fields.Date.from_string(data.get('date_to'))
        employee_ids = data.get('employee_ids')

        employees = self.env['hr.employee'].browse(employee_ids)
        dates = [date_from + timedelta(days=i) for i in range((date_to - date_from).days + 1)]

        attendance_data = self.env['report.agp_attendance_ib.attendance_excel_report']._get_attendance_data(
            employee_ids, date_from, date_to)
        leave_data = self.env['report.agp_attendance_ib.attendance_excel_report']._get_leave_data(employee_ids,
                                                                                                  date_from, date_to)
        business_trip_data = self.env['report.agp_attendance_ib.attendance_excel_report']._get_business_trip_data(
            employee_ids, date_from, date_to)

        return {
            'doc_ids': docids,
            'doc_model': 'hr.attendance',
            'data': data,
            'employees': employees,
            'dates': dates,
            'attendance_data': attendance_data,
            'leave_data': leave_data,
            'business_trip_data': business_trip_data,
        }