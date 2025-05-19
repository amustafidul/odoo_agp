from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter


class LabaRugiCabangController(http.Controller):
    @http.route([
        '/laba_rugi_cabang/export/<model("laba.rugi.mb.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_laba_rugi_cabang(self, wizard_id=False, **args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('LABA RUGI CABANG.xlsx'))
                    ]
                )

        # vals = self.get_value(wizard_id)
        
        # buat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # buat style untuk mengatur jenis font, ukuran font, border dan alligment
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'left'})
        header_style = workbook.add_format({'bottom': 2, 'align': 'center'})

        sheet = workbook.add_worksheet()
        # set orientation jadi landscape
        sheet.set_landscape()
        # set ukuran kertas, 9 artinya kertas A4
        sheet.set_paper(9)
        # set margin kertas dalam satuan inchi
        # sheet.set_margins(2,2,2,2)

        # set lebar kolom
        # sheet.set_column('B:B',0,0,{'hidden': True})
        sheet.set_column('A:B', 50)
        sheet.set_column('C:Z', 15)
        
        row = 1
        sheet.write(f'A{row}', 'LABA RUGI CABANG', title_style)
        row += 1
        periode = f"{wizard_id.date_to.strftime('%m')} - {wizard_id.date_to.strftime('%Y')}"
        sheet.write(f'A{row}', f"""Periode : {periode}""", title_style)
        row += 3
        sheet.write(f'A{row}', 'KODE', header_style)
        sheet.write(f'B{row}', 'NAMA PERKIRAAN', header_style)
        sheet.write(f'C{row}', 'KONSOLIDASI', header_style)
        colhead = 3
        branchs = wizard_id.get_list_branch()
        for branch in branchs:
            sheet.write(row - 1, colhead, branch['name'], header_style)
            colhead += 1
        row += 1


        account_lines = wizard_id.compute_formula(wizard_id.date_from, wizard_id.date_to)
        for account in account_lines:
            text_style = workbook.add_format({'bold': False, 'align': 'left'})
            float_style = workbook.add_format({'bold': False, 'align': 'right', 'num_format': '#,##0.00'})
            if account.get('bold'):
                text_style = workbook.add_format({'bold': True, 'align': 'left'})
                float_style = workbook.add_format({'bold': True, 'align': 'right', 'num_format': '#,##0.00'})
            if account.get('blank'):
                float_style = workbook.add_format({'color': 'white'})
            
            # Check if the account name is a code followed by a name
            account_name_parts = account['name'].split(' ', 1)
            if len(account_name_parts) == 2 and account_name_parts[0].isdigit():
                account_code = account_name_parts[0]  # The first part is the code
                account_name = account_name_parts[1]  # The second part is the name
            else:
                account_code = ''  # No code, so leave this empty
                account_name = account['name']  # Use the full string as the name
                    
            # Write to Excel sheet
            sheet.write(f'A{row}', account_code, text_style)
            sheet.write(f'B{row}', account_name, text_style)            
            sheet.write(f'C{row}', account['balance'], float_style)
            
            # Initialize the starting column for branch balances
            colbody = 3

            for branch in account['branch_list_vals']:
                sheet.write(row - 1, colbody, branch['balance'], float_style)
                colbody += 1
            
            row += 1
        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response
