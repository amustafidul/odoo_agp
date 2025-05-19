from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter


class CompareTaxController(http.Controller):
    @http.route([
        '/compare_tax/export/<model("compare.tax.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_compare_tax(self, wizard_id=False, **args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Compare Tax.xlsx'))
                    ]
                )
        
        # Buat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Buat style untuk mengatur jenis font, ukuran font, border, dan alignment
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'bg_color': '#0000ff', 'bold': True, 'border': 1, 'align': 'center'})
        body_center_border = workbook.add_format({'border': 1, 'align': 'center'})
        body_left_border = workbook.add_format({'border': 1, 'align': 'left'})
        number_border = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'right'})
        compare_style_match = workbook.add_format({'bg_color': '#008000', 'num_format': '#,##0.00', 'border': 1, 'align': 'right'})
        compare_style_mismatch = workbook.add_format({'bg_color': '#FF0000', 'num_format': '#,##0.00', 'border': 1, 'align': 'right'})

        # Buat worksheet
        sheet = workbook.add_worksheet()

        # Set orientation jadi landscape dan ukuran kertas A4
        sheet.set_landscape()
        sheet.set_paper(9)

        # Set lebar kolom
        sheet.set_column('A:G', 20)

        # Tulis judul dan header
        row = 1
        sheet.merge_range(f'A{row}:G{row}', 'Compare Tax', title_style)
        row += 1
        headers = ['No NPWP', 'Nama PT', 'No Faktur', 'Total Pembelian', 'Total Pajak Tarikan', 'Total Pajak Odoo', 'Invoice']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_style_border)

        # Tulis data
        row += 1
        lines = wizard_id.get_lines()
        for line in lines:
            compare_style = compare_style_match if line['nominal_ppn'] == line['total_pajak_odoo'] else compare_style_mismatch

            sheet.write(row, 0, line['no_npwp'], body_left_border)
            sheet.write(row, 1, line['nama_pt'], body_left_border)
            sheet.write(row, 2, line['no_faktur'], body_left_border)
            sheet.write(row, 3, line['nominal_invoice'], number_border)
            sheet.write(row, 4, line['nominal_ppn'], compare_style)
            sheet.write(row, 5, line['total_pajak_odoo'], compare_style)
            sheet.write(row, 6, line['invoice'], body_left_border)
            row += 1

        # Tutup workbook dan output
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response
