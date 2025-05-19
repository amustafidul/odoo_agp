from odoo import models, fields, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class AttendanceExcelReport(models.AbstractModel):
    _name = 'report.agp_attendance_ib.attendance_excel_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Attendance Excel Report'

    def generate_xlsx_report(self, workbook, data, lines):
        date_from = fields.Date.from_string(data['date_from'])
        date_to = fields.Date.from_string(data['date_to'])
        employee_ids = data['employee_ids']

        if not employee_ids or not date_from or not date_to:
            _logger.warning("Tidak ada data yang dipilih untuk laporan kehadiran.")
            return

        # Fetch employee names
        employees = self.env['hr.employee'].browse(employee_ids)
        employee_data = {emp.id: emp.name for emp in employees}

        # Determine max name length for column width
        max_name_length = max(len(name) for name in employee_data.values()) + 2

        # Create Worksheet
        sheet = workbook.add_worksheet('Laporan Kehadiran')
        title_format = workbook.add_format({'bold': True, 'align': 'center', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#CCCCCC'})
        weekend_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FF6666'})
        cell_format = workbook.add_format({'align': 'center'})
        left_align_format = workbook.add_format({'align': 'left'})

        # Header Title
        total_days = (date_to - date_from).days + 1
        sheet.merge_range(0, 0, 0, total_days, "Data Kehadiran, Cuti, dan Dinas Karyawan", title_format)
        sheet.merge_range(
            1, 0, 1, total_days,
            f"Periode: {date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}",
            cell_format
        )

        # Date headers
        sheet.write(3, 0, "Nama", header_format)
        dates = [date_from + timedelta(days=i) for i in range(total_days)]
        for col_idx, date in enumerate(dates, start=1):
            fmt = weekend_format if date.weekday() >= 5 else header_format
            sheet.write(3, col_idx, date.strftime('%d/%m'), fmt)

        # Set column width
        sheet.set_column(0, 0, max_name_length)

        # Fetch data
        attendance_data = self._get_attendance_data(employee_ids, date_from, date_to)
        leave_data = self._get_leave_data(employee_ids, date_from, date_to)
        business_trip_data = self._get_business_trip_data(employee_ids, date_from, date_to)

        # Write data to worksheet
        for row_idx, emp_id in enumerate(employee_ids, start=4):
            row = [employee_data.get(emp_id, "Unknown")]
            for date in dates:
                if date in business_trip_data.get(emp_id, {}):
                    row.append(business_trip_data[emp_id][date])
                elif date in leave_data.get(emp_id, {}):
                    row.append(leave_data[emp_id][date])
                elif date in attendance_data.get(emp_id, {}):
                    check_in, check_out, is_late, late_minutes = attendance_data[emp_id][date]
                    if is_late:
                        row.append(
                            f"{check_in.strftime('%H:%M')} - "
                            f"{check_out.strftime('%H:%M') if check_out else '--'} "
                            f"(Telat {late_minutes} menit)"
                        )
                    else:
                        row.append(
                            f"{check_in.strftime('%H:%M')} - "
                            f"{check_out.strftime('%H:%M') if check_out else '--'}"
                        )
                else:
                    row.append("-")

            sheet.write_row(row_idx, 0, row, cell_format)

    def _get_attendance_data(self, employee_ids, date_from, date_to):
        records = self.env['hr.attendance'].search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', date_from.strftime('%Y-%m-%d 00:00:00')),
            ('check_out', '<=', date_to.strftime('%Y-%m-%d 23:59:59')),
        ])

        attendance_dict = {}

        schedule_ids = records.mapped('employee_id.resource_calendar_id').ids

        all_cal_att = self.env['resource.calendar.attendance'].search([
            ('calendar_id', 'in', schedule_ids),
            ('day_period', '=', 'morning')
        ])

        cal_att_map = {}
        for cal_att in all_cal_att:
            key = (cal_att.calendar_id.id, cal_att.dayofweek)
            cal_att_map[key] = cal_att.hour_from

        for rec in records:
            check_in_date = rec.check_in.date()

            check_in = rec.check_in + timedelta(hours=7)
            check_out = rec.check_out + timedelta(hours=7) if rec.check_out else None

            employee = rec.employee_id
            schedule = employee.resource_calendar_id
            day_of_week_str = str(check_in.weekday())

            # Default
            expected_check_in = None
            late_minutes = 0
            is_late = False

            if schedule and (schedule.id, day_of_week_str) in cal_att_map:
                hour_from = cal_att_map[(schedule.id, day_of_week_str)]
                expected_check_in = check_in.replace(hour=int(hour_from), minute=0, second=0)

                # Cek keterlambatan
                if check_in > expected_check_in:
                    late_minutes = int((check_in - expected_check_in).total_seconds() / 60)
                    is_late = True

            attendance_dict.setdefault(employee.id, {})[check_in_date] = (
                check_in,
                check_out,
                is_late,
                late_minutes
            )

        return attendance_dict

    def _get_leave_data(self, employee_ids, date_from, date_to):
        """Fetch leave data for employees in date range."""
        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids),
            ('request_date_from', '<=', date_to),
            ('request_date_to', '>=', date_from),
            ('state', 'in', ['validate','approved'])
        ])
        leave_dict = {}
        for leave in leaves:
            current_date = max(leave.request_date_from, date_from)
            while current_date <= min(leave.request_date_to, date_to):
                # Hanya catat di hari kerja (weekday < 5) atau sesuai kebutuhan
                if current_date.weekday() < 5:
                    leave_dict.setdefault(leave.employee_id.id, {})[current_date] = (
                        f"{leave.holiday_status_id.name}"
                    )
                current_date += timedelta(days=1)
        return leave_dict

    def _get_business_trip_data(self, employee_ids, date_from, date_to):
        """Fetch business trip (dinas) data."""
        trips = self.env['hr.leave.dinas'].search([
            ('assigner_id', 'in', employee_ids),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('state', 'in', ['approved','dinas_tiba','dinas_selesai'])
        ])
        business_trip_dict = {}
        for trip in trips:
            current_date = max(trip.date_from, date_from)
            while current_date <= min(trip.date_to, date_to):
                business_trip_dict.setdefault(trip.employee_id.id, {})[current_date] = (
                    f"Dinas ke {trip.destination_place or 'Tidak ada lokasi'}"
                )
                current_date += timedelta(days=1)
        return business_trip_dict