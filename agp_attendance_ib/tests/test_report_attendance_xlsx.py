from odoo.tests import common
from datetime import date, datetime
import cProfile
import io
import xlsxwriter


class TestAttendanceExcelReport(common.TransactionCase):
    def setUp(self):
        super(TestAttendanceExcelReport, self).setUp()
        self.report_model = self.env['report.agp_attendance_ib.attendance_excel_report']
        self.employee_model = self.env['hr.employee']
        self.attendance_model = self.env['hr.attendance']
        self.leave_model = self.env['hr.leave']
        self.business_trip_model = self.env['hr.leave.dinas']

        self.employees = [self.employee_model.create({'name': f'Employee {i}'}) for i in range(10)]

        self.attendances = []
        for employee in self.employees:
            for day in range(1, 32):
                try:
                    check_in = datetime(2023, 1, day, 8, 0)
                    check_out = datetime(2023, 1, day, 16, 0)
                    self.attendances.append(self.attendance_model.create({
                        'employee_id': employee.id,
                        'check_in': check_in,
                        'check_out': check_out,
                    }))
                except ValueError:
                    pass  # Skip days that don't exist in January

        leave_type = self.env['hr.leave.type'].create({'name': 'Cuti Tahunan'})
        self.leaves = []
        for employee in self.employees[::2]:
            for day in range(1, 320, 7):
                try:
                    request_date_from = date(2023, 1, day)
                    request_date_to = date(2025, 1, day + 1)
                    existing_leaves = self.leave_model.search([
                        ('employee_id', '=', employee.id),
                        ('request_date_from', '<=', request_date_to),
                        ('request_date_to', '>=', request_date_from)
                    ])
                    if not existing_leaves:
                        self.leaves.append(self.leave_model.create({
                            'employee_id': employee.id,
                            'request_date_from': request_date_from,
                            'request_date_to': request_date_to,
                            'holiday_status_id': leave_type.id,
                        }))
                except ValueError:
                    pass  # Skip days that don't exist in January

        self.business_trips = []
        for employee in self.employees[1::2]:
            for day in range(1, 32, 5):
                try:
                    date_from = date(2023, 1, day)
                    date_to = date(2023, 1, day + 1)
                    self.business_trips.append(self.business_trip_model.create({
                        'employee_id': employee.id,
                        'date_from': date_from,
                        'date_to': date_to,
                        'destination_place': 'Jakarta',
                    }))
                except ValueError:
                    pass  # Skip days that don't exist in January

    def test_generate_xlsx_report_with_large_data(self):
        data = {
            'date_from': date(2023, 1, 1),
            'date_to': date(2025, 1, 31),
            'employee_ids': self.env['hr.employee'].search([]).ids,
            'all_employee': True,
        }

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        profiler = cProfile.Profile()
        profiler.enable()

        self.report_model.generate_xlsx_report(workbook, data, [])