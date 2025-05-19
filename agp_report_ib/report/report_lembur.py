from odoo import models, fields, api


class ReportOvertime(models.AbstractModel):
    _name = 'report.agp_report_ib.report_overtime_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Overtime Report in Excel'

    def generate_xlsx_report(self, workbook, data, lines):
        worksheet = workbook.add_worksheet("Overtime Report")

        # Define formats
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#FFA07A', 'border': 1})
        cell_format = workbook.add_format({'border': 1, 'align': 'left'})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1, 'align': 'left'})

        # Header
        headers = ['Employees', 'Penempatan', 'Description', 'Tanggal', 'Duration Waktu Lembur', 'Status']
        worksheet.write_row(0, 0, headers, header_format)

        leave_records = self.env['hr.leave.lembur']

        if data['form']['select_all_employees']:
            leave_records |= self.env['hr.leave.lembur'].search([
                ('new_date_field', '>=', data['form']['start_date']),
                ('new_date_field', '<=', data['form']['end_date']),
            ])
        else:
            leave_records |= self.env['hr.leave.lembur'].search([
                ('new_date_field', '>=', data['form']['start_date']),
                ('new_date_field', '<=', data['form']['end_date']),
                ('all_employee_ids', 'in', data['form']['employee_ids']),
            ])

        row = 1
        for record in leave_records:
            worksheet.write(row, 0, record.employee_id.name, cell_format)
            worksheet.write(row, 1, record.lembur_location_id.name, cell_format)
            worksheet.write(row, 2, record.name if record.name else '-', cell_format)
            worksheet.write_datetime(row, 3, record.new_date_field, date_format)
            worksheet.write(row, 4, record.duration_waktu_lembur, cell_format)
            state = ''
            if record.state == 'draft':
                state = 'To Submit'
            elif record.state == 'confirm':
                state = 'To Approve'
            elif record.state == 'refuse':
                state = 'Refused'
            elif record.state == 'validate1':
                state = 'Second Approval'
            elif record.state == 'validate' or record.state == 'approved':
                state = 'Approved'
            elif record.state == 'on_review':
                state = 'On Review'
            elif record.state == 'rejected':
                state = 'Rejected'
            elif record.state == 'ask_for_revision':
                state = 'Ask For Revision'
            worksheet.write(row, 5, state, cell_format)
            row += 1

        # Auto-adjust column width
        for col in range(len(headers)):
            worksheet.set_column(col, col, 20)