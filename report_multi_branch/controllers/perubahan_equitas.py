from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

import babel


class PerubahanEquitasController(http.Controller):
    @http.route([
        '/perubahan_equitas/export/<model("perubahan.equitas.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_perubahan_equitas(self, wizard_id=False, **args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Laporan Perubahan Ekuitas Konsolidasian.xlsx'))
                    ]
                )
        
        # buat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # buat style untuk mengatur jenis font, ukuran font, border dan alligment
        title_style_left = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'left'})
        title_style_right = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'right'})
        header_style = workbook.add_format({'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'text_wrap': True, 'bottom': 2, 'bold': True, 'align': 'center'})
        text_style = workbook.add_format({'align': 'left'})
        float_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})

        sheet = workbook.add_worksheet()
        # set orientation jadi landscape
        sheet.set_landscape()
        # set ukuran kertas, 9 artinya kertas A4
        sheet.set_paper(9)
        # set margin kertas dalam satuan inchi
        # sheet.set_margins(2,2,2,2)

        # set lebar kolom
        # sheet.set_column('B:B',0,0,{'hidden': True})
        sheet.set_column('A:J', 20)
        
        previous_year = str(int(wizard_id.periode) - 1)
        current_year = str(wizard_id.periode)
        
        row = 1
        col = 0
        sheet.write(row - 1, col, 'PT ADHI GUNA PUTERA', title_style_left)
        sheet.write(row - 1, col + 9, 'PT ADHI GUNA PUTERA', title_style_right)
        row += 1
        sheet.write(row - 1, col, '  DAN ENTITAS ANAK', title_style_left)
        sheet.write(row - 1, col + 9, '  AND ITS SUBSIDIARY', title_style_right)
        row += 1
        sheet.write(row - 1, col, 'LAPORAN PERUBAHAN EKUITAS KONSOLIDASIAN', title_style_left)
        sheet.write(row - 1, col + 9, 'CONSOLIDATED STATEMENT OF CHANGES IN EQUITY', title_style_right)
        row += 1
        sheet.write(row - 1, col, f'Untuk tahun yang Berakhir {previous_year}', title_style_left)
        sheet.write(row - 1, col + 9, f'For the Year Ended 31, {current_year}', title_style_right)
        
        row += 1
        sheet.write(row - 1, col, '(dalam Rupiah)', title_style_left)
        sheet.write(row - 1, col + 9, '(expressed in Rupiah)', title_style_right)
        
        row += 3
        sheet.merge_range(row - 1, col, row - 1, col + 9, '', workbook.add_format({'top': 2}))
        
        row += 2
        sheet.merge_range(f'B{row}:G{row}', 'Diatribusikan Kepada Pemilik Entitas Induk', header_style_border)
        
        row += 1
        sheet.merge_range(f'D{row}:F{row}', 'Saldo laba/ Retained earing', header_style_border)
        
        row += 1
        sheet.write(f'B{row}', 'Modal saham/ \n Shares capital', header_style_border)
        sheet.write(f'C{row}', 'Tambahan modal disetor/ \n Additional paid in capital', header_style_border)
        sheet.write(f'D{row}', 'Ditentukan Penggunanya/ \n Specified Use', header_style_border)
        sheet.write(f'E{row}', 'Tidak Ditentukan Penggunaannya/ \n Not Specified Use', header_style_border)
        sheet.write(f'F{row}', 'Penghasilan Komprehensif Lain/ \n Other comprehensive income', header_style_border)
        sheet.write(f'G{row}', 'Jumlah/ \n Amount', header_style_border)
        sheet.write(f'H{row}', 'Diatribusikan kepada Kepentingan Non-Pengendali/ \n Attribute to Interests Non-Controller', header_style_border)
        sheet.write(f'I{row}', 'Jumlah Ekuitas/ \n Amount of Equity', header_style_border)

        # ============================================================
        row += 1
        pre_B2 = self.get_value("('3101002')", previous_year)
        pre_C2 = self.get_value("('3203002')", previous_year)
        pre_total_G2 = pre_B2['balance'] + pre_C2['balance']
        sheet.write(f'A{row}', f'Saldo per 1 Januari {previous_year}', text_style)
        sheet.write(f'B{row}', pre_B2['balance'], float_style)
        sheet.write(f'C{row}', pre_C2['balance'], float_style)
        sheet.write(f'G{row}', pre_total_G2, float_style)
        sheet.write(f'J{row}', f'Balance of January 1, {previous_year}', text_style)
        row += 1
        pre_E3 = self.get_value("('2203101', '2203102', '2203103')", previous_year)
        pre_total_G3 = pre_E3['balance']
        sheet.write(f'A{row}', 'Dividen', text_style)
        sheet.write(f'E{row}', pre_E3['balance'], float_style)
        sheet.write(f'G{row}', pre_total_G3, float_style)
        sheet.write(f'J{row}', 'Dividen', text_style)
        row += 1
        pre_E4 = self.get_value("('3302001')", previous_year)
        pre_total_G4 = pre_E4['balance']
        sheet.write(f'A{row}', f'Laba bersih tahun {previous_year}', text_style)
        sheet.write(f'E{row}', pre_E4['balance'], float_style)
        sheet.write(f'G{row}', pre_total_G4, float_style)
        sheet.write(f'J{row}', f'Net profit {previous_year}', text_style)
        row += 1
        pre_F5 = self.get_value("('9900003','9900004')", previous_year)
        pre_total_G5 = pre_F5['balance']
        sheet.write(f'A{row}', 'Pengukuran kembali atas program imbalan pasti', text_style)
        sheet.write(f'F{row}', pre_F5['balance'], float_style)
        sheet.write(f'G{row}', pre_total_G5, float_style)
        sheet.write(f'J{row}', 'Remeasurement of defined benefits pension plan', text_style)
        row += 1
        pre_total_B6 = pre_B2['balance']
        pre_total_C6 = pre_C2['balance']
        pre_total_E6 = pre_E3['balance'] + pre_E4['balance']
        pre_total_F6 = pre_F5['balance']

        pre_total_G6 = pre_total_G2 + pre_total_G3 + pre_total_G4 + pre_total_G5
        sheet.write(f'A{row}', f'Saldo per 31 Desember {previous_year}', text_style)
        sheet.write(f'B{row}', pre_total_B6, float_style)
        sheet.write(f'C{row}', pre_total_C6, float_style)
        sheet.write(f'E{row}', pre_total_E6, float_style)
        sheet.write(f'F{row}', pre_total_F6, float_style)
        sheet.write(f'G{row}', pre_total_G6, float_style)
        sheet.write(f'J{row}', f'Balance of December 31, {previous_year}', text_style)
        
        
        # ============================================================
        row += 3
        cur_B2 = self.get_value("('3101002')", current_year)
        cur_C2 = self.get_value("('3203002')", current_year)
        cur_total_G2 = cur_B2['balance'] + cur_C2['balance']
        sheet.write(f'A{row}', f'Saldo per 1 Januari {current_year}', text_style)
        sheet.write(f'B{row}', cur_B2['balance'], float_style)
        sheet.write(f'C{row}', cur_C2['balance'], float_style)
        sheet.write(f'G{row}', cur_total_G2, float_style)
        sheet.write(f'J{row}', f'Balance of January 1, {current_year}', text_style)
        row += 1
        cur_E3 = self.get_value("('2203101', '2203102', '2203103')", current_year)
        cur_total_G3 = cur_E3['balance']
        sheet.write(f'A{row}', 'Dividen', text_style)
        sheet.write(f'E{row}', cur_E3['balance'], float_style)
        sheet.write(f'G{row}', cur_total_G3, float_style)
        sheet.write(f'J{row}', 'Dividen', text_style)
        row += 1
        cur_E4 = self.get_value("('3302001')", current_year)
        cur_total_G4 = cur_E4['balance']
        sheet.write(f'A{row}', f'Laba bersih tahun {current_year}', text_style)
        sheet.write(f'E{row}', cur_E4['balance'], float_style)
        sheet.write(f'G{row}', cur_total_G4, float_style)
        sheet.write(f'J{row}', f'Net profit {current_year}', text_style)
        row += 1
        cur_F5 = self.get_value("('9900003','9900004')", current_year)
        cur_total_G5 = cur_F5['balance']
        sheet.write(f'A{row}', 'Pengukuran kembali atas program imbalan pasti', text_style)
        sheet.write(f'F{row}', cur_F5['balance'], float_style)
        sheet.write(f'G{row}', cur_total_G5, float_style)
        sheet.write(f'J{row}', 'Remeasurement of defined benefits pension plan', text_style)
        row += 1
        cur_total_B6 = cur_B2['balance']
        cur_total_C6 = cur_C2['balance']
        cur_total_E6 = cur_E3['balance'] + cur_E4['balance']
        cur_total_F6 = cur_F5['balance']

        cur_total_G6 = cur_total_G2 + cur_total_G3 + cur_total_G4 + cur_total_G5
        sheet.write(f'A{row}', f'Saldo per 31 Desember {current_year}', text_style)
        sheet.write(f'B{row}', cur_total_B6, float_style)
        sheet.write(f'C{row}', cur_total_C6, float_style)
        sheet.write(f'E{row}', cur_total_E6, float_style)
        sheet.write(f'F{row}', cur_total_F6, float_style)
        sheet.write(f'G{row}', cur_total_G6, float_style)
        sheet.write(f'J{row}', f'Balance of December 31, {current_year}', text_style)

        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response

    
    def get_value(self, code_accounts, year):
        request._cr.execute(f"""
        select ABS(COALESCE(SUM(aml.balance), 0)) as balance
        from account_move_line aml
        join account_move am on aml.move_id = am.id
        join account_account aa on aml.account_id = aa.id
        where am.state = 'posted' and aa.code in {code_accounts} and EXTRACT(YEAR FROM aml.date) = {year}
        """)
        result = request._cr.dictfetchone()
        return result