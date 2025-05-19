from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

import babel


class LabaRugiSummaryController(http.Controller):
    @http.route([
        '/laba_rugi_summary/export/<model("laba_rugi.summary.mb.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_laba_rugi_summary(self, wizard_id=False, **args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Laporan Laba Rugi Summary.xlsx'))
                    ]
                )
        
        # buat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # buat style untuk mengatur jenis font, ukuran font, border dan alligment
        title_style_left = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'left'})
        title_style_right = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'right'})
        header_style = workbook.add_format({'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'bottom': 1, 'bold': True, 'align': 'center'})

        sheet = workbook.add_worksheet()
        # set orientation jadi landscape
        sheet.set_landscape()
        # set ukuran kertas, 9 artinya kertas A4
        sheet.set_paper(9)
        # set margin kertas dalam satuan inchi
        # sheet.set_margins(2,2,2,2)

        # set lebar kolom
        # sheet.set_column('B:B',0,0,{'hidden': True})
        sheet.set_column('A:A', 50)
        sheet.set_column('B:D', 30)
        sheet.set_column('E:E', 50)
        
        previous_year = int(wizard_id.periode) - 1
        current_year = wizard_id.periode
        
        row = 1
        col = 0
        sheet.write(row - 1, col, 'PT ADHI GUNA PUTERA', title_style_left)
        sheet.write(row - 1, col + 4, 'PT ADHI GUNA PUTERA', title_style_right)
        row += 1
        sheet.write(row - 1, col, '  DAN ENTITAS ANAK', title_style_left)
        sheet.write(row - 1, col + 4, '  AND ITS SUBSIDIARY', title_style_right)
        row += 1
        sheet.write(row - 1, col, 'LAPORAN LABA RUGI DAN PENGHASILAN', title_style_left)
        sheet.write(row - 1, col + 4, 'CONSOLIDATED STATEMENT OF PROFIT OR LOSE', title_style_right)
        row += 1
        sheet.write(row - 1, col, '  KOMPREHENSIF LAIN KONSOLIDASIAN', title_style_left)
        sheet.write(row - 1, col + 4, '  AND OTHER COMPREHENSIVE INCOME', title_style_right)
        row += 1
        
        sheet.write(row - 1, col, f'Untuk Tahun yang Berakhir 31 Desember {str(current_year)}', title_style_left)
        sheet.write(row - 1, col + 4, f'For the Year Ended December 31, {str(current_year)}', title_style_right)
        
        row += 1
        sheet.write(row - 1, col, '(dalam Rupiah)', title_style_left)
        sheet.write(row - 1, col + 4, '(expressed in Rupiah)', title_style_right)
        
        row += 2
        sheet.merge_range(row - 1, col, row - 1, col + 4, '', workbook.add_format({'top': 2}))
        row += 1
        sheet.write(row - 1, col, '', header_style)
        sheet.write(row - 1, col + 1, 'Catatan/Notes', header_style_border)
        sheet.write(row - 1, col + 2, str(current_year), header_style_border)
        sheet.write(row - 1, col + 3, str(previous_year), header_style_border)
        sheet.write(row - 1, col + 4, '', header_style)
        row += 1

        # account_lines = wizard_id.get_account_lines()
        # for account in account_lines:
        #     if account['level'] != 0:
        #         text_style1 = workbook.add_format({'bold': True, 'align': 'left'})
        #         text_style2 = workbook.add_format({'bold': True, 'align': 'right'})
        #         float_style = workbook.add_format({'bold': True, 'align': 'right', 'num_format': '#,##0.00'})
        #         if account['type'] == 'subline':
        #             text_style1 = workbook.add_format({'bold': False, 'align': 'left'})
        #             text_style2 = workbook.add_format({'bold': False, 'align': 'right'})
        #             float_style = workbook.add_format({'bold': False, 'align': 'right', 'num_format': '#,##0.00'})
        #         sheet.write(f'A{row}', account['name1'], text_style1)
        #         sheet.write(f'B{row}', '', text_style1)
        #         sheet.write(f'C{row}', '', text_style1)
        #         sheet.write(f'D{row}', '', text_style1)
        #         sheet.write(f'E{row}', account['name2'], text_style2)
        #         if account['type'] in ['subline','total']:
        #             sheet.write(f'B{row}', '', text_style1)
        #             sheet.write(f'C{row}', account['balance1'], float_style)
        #             sheet.write(f'D{row}', account['balance2'], float_style)
        #             sheet.write(f'E{row}', account['name2'], text_style2)
                
        #         row += 1

        wizard_id.compute_formula(previous_year, current_year)
        account_lines = []
        for line in wizard_id.financial_param_id.sub_param_ids.filtered(lambda x:not x.invisible):
            account_lines.append({
                'name1': line.name,
                'name2': line.name_eng,
                'balance1': line.balance1,
                'balance2': line.balance2,
                'type': line.type,
                'level': line.level,
                'bold': line.bold,
                'blank': line.blank,
            })
        
        for account in account_lines:
            text_style = workbook.add_format({'bold': False, 'align': 'left'})
            float_style = workbook.add_format({'bold': False, 'align': 'right', 'num_format': '#,##0.00'})
            if account.get('bold'):
                text_style = workbook.add_format({'bold': True, 'align': 'left'})
                float_style = workbook.add_format({'bold': True, 'align': 'right', 'num_format': '#,##0.00'})
            if account.get('blank'):
                float_style = workbook.add_format({'color': 'white'})
            
            sheet.write(f'A{row}', account['name1'], text_style)
            sheet.write(f'B{row}', '', text_style)
            sheet.write(f'C{row}', account['balance1'], float_style)
            sheet.write(f'D{row}', account['balance2'], float_style)
            sheet.write(f'E{row}', account['name2'], text_style)
            
            row += 1


        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response