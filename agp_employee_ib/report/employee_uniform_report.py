from odoo import models, fields, api
import io
import xlsxwriter
import base64


class EmployeeUniformReport(models.TransientModel):
    _name = 'employee.uniform.report'
    _description = 'Employee Uniform Report'

    date_from = fields.Date(string='Tanggal Dari')
    date_to = fields.Date(string='Tanggal Sampai')

    def action_print_report(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        self._create_sheet_summary(workbook)
        self._create_sheet_detail(workbook)
        workbook.close()
        output.seek(0)
        return self._download_excel(output)

    def _create_sheet_summary(self, workbook):
        sheet = workbook.add_worksheet('Rekap Kebutuhan Seragam Batik')

        # Define formats
        header_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0', 'align': 'right', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        total_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1})

        # Set column widths
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 10)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 25)
        sheet.set_column('F:F', 25)

        # Write merged headers
        sheet.merge_range('A1:A2', 'NO', header_format)
        sheet.merge_range('B1:B2', 'KETERANGAN', header_format)
        sheet.merge_range('C1:C2', 'JUMLAH', header_format)
        sheet.merge_range('D1:E1', 'HARGA', header_format)
        sheet.write('D2', 'LENGAN PENDEK', header_format)
        sheet.write('E2', 'LENGAN PANJANG', header_format)

        row = 2
        col = 0

        # Fetch data from model
        selected_uniforms = self.env['employee.uniform'].search([
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to)
        ])

        # Aggregate data by uniform and sleeve type
        summary_data = {}
        for uniform in selected_uniforms:
            key = uniform.uniform_id.name
            if key not in summary_data:
                summary_data[key] = {'jumlah': 0, 'harga_lengan_pendek': 0, 'harga_lengan_panjang': 0}
            summary_data[key]['jumlah'] += 1
            if uniform.lengan == 'pendek':
                summary_data[key]['harga_lengan_pendek'] += uniform.harga_lengan_pendek_l
                summary_data[key]['harga_lengan_panjang'] = 0
            elif uniform.lengan == 'panjang':
                summary_data[key]['harga_lengan_pendek'] = 0
                summary_data[key]['harga_lengan_panjang'] += uniform.harga_lengan_panjang_xl

        # Write data to sheet
        total_jumlah = 0
        total_lengan_pendek = 0
        total_lengan_panjang = 0

        for i, (key, data) in enumerate(summary_data.items()):
            sheet.write(row, col, i + 1, text_format)  # NO
            sheet.write(row, col + 1, key, text_format)  # KETERANGAN
            sheet.write(row, col + 2, data['jumlah'], text_format)  # JUMLAH
            sheet.write_number(row, col + 3, data['harga_lengan_pendek'], currency_format)  # LENGAN PENDEK
            sheet.write_number(row, col + 4, data['harga_lengan_panjang'], currency_format)  # LENGAN PANJANG

            total_jumlah += data['jumlah']
            total_lengan_pendek += data['harga_lengan_pendek']
            total_lengan_panjang += data['harga_lengan_panjang']

            row += 1

        # Write totals row
        sheet.merge_range(row, 0, row + 1, 2, 'JUMLAH', total_format)  # Merge JUMLAH from column 0 to 2 and rows
        sheet.write(row, 3, total_lengan_pendek, total_format)
        sheet.write(row, 4, total_lengan_panjang, total_format)

        # Row for summed totals
        row += 1
        total_sum = total_lengan_pendek + total_lengan_panjang
        sheet.write(row, 2, '', total_format)
        sheet.merge_range(row, 3, row, 4, total_sum, total_format)

    def _create_sheet_detail(self, workbook):
        sheet = workbook.add_worksheet('Rincian Seragam')
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0', 'align': 'right', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        total_format = workbook.add_format(
            {'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 30)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 25)
        sheet.set_column('F:F', 25)

        sheet.merge_range('A1:A2', 'NO', header_format)
        sheet.merge_range('B1:B2', 'NAMA', header_format)
        sheet.merge_range('C1:C2', 'KETERANGAN', header_format)
        sheet.merge_range('D1:D2', 'L/P', header_format)
        sheet.merge_range('E1:F1', 'HARGA', header_format)
        sheet.write('E2', 'LENGAN PENDEK', header_format)
        sheet.write('F2', 'LENGAN PANJANG', header_format)

        row = 2
        col = 0
        selected_uniforms = self.env['employee.uniform'].search([
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to)
        ])

        total_harga_lengan_pendek = 0
        total_harga_lengan_panjang = 0
        for i, uniform in enumerate(selected_uniforms):
            sheet.write(row, col, i + 1, text_format)
            sheet.write(row, col + 1, uniform.employee_id.name, text_format)
            sheet.write(row, col + 2, uniform.uniform_id.name, text_format)
            sheet.write(row, col + 3, 'L' if uniform.employee_id.gender == 'male' else ('P' if uniform.employee_id.gender == 'female' else '-'), text_format)


            if uniform.lengan == 'pendek':
                total_harga_lengan_pendek += uniform.harga_lengan_pendek_xl
                sheet.write(row, col + 4, uniform.harga_lengan_pendek, currency_format)
                sheet.write(row, col + 5, 0, currency_format)
            elif uniform.lengan == 'panjang':
                total_harga_lengan_panjang += uniform.harga_lengan_panjang_xl
                sheet.write(row, col + 4, 0, currency_format)
                sheet.write(row, col + 5, uniform.harga_lengan_panjang, currency_format)

            row += 1

        # Write totals row
        sheet.merge_range(row, 0, row + 1, 3, 'JUMLAH', total_format)
        sheet.write(row, 4, total_harga_lengan_pendek, total_format)
        sheet.write(row, 5, total_harga_lengan_panjang, total_format)

        row += 1
        total_sum = total_harga_lengan_pendek + total_harga_lengan_panjang
        sheet.merge_range(row, 4, row, 5, total_sum, total_format)

    def _download_excel(self, output):
        filename = 'Rekap_Seragam_Batik.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=ir.attachment&id=%s&filename=%s&field=datas&download=true' % (
                self.env['ir.attachment'].create({
                    'name': filename,
                    'datas': base64.b64encode(output.read()),
                    'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                }).id,
                filename
            ),
            'target': 'new',
        }