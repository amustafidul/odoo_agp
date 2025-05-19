from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

# Ahmad version
# class NeracaController(http.Controller):
#     @http.route([
#         '/neraca/export/<model("neraca.mb.wizard"):wizard_id>',
#     ], type='http', auth='user', csrf=False)
#     def export_neraca(self, wizard_id=False, **args):
#         response = request.make_response(
#                     None,
#                     headers=[
#                         ('Content-Type', 'application/vnd.ms-excel'),
#                         ('Content-Disposition', content_disposition('NERACA.xlsx'))
#                     ]
#                 )

#         # vals = self.get_value(wizard_id)
        
#         # buat object workbook dari library xlsxwriter
#         output = io.BytesIO()
#         workbook = xlsxwriter.Workbook(output, {'in_memory': True})
#         # buat style untuk mengatur jenis font, ukuran font, border dan alligment
#         title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'left'})
#         header_style = workbook.add_format({'bottom': 2, 'align': 'center'})

#         sheet = workbook.add_worksheet()
#         # set orientation jadi landscape
#         sheet.set_landscape()
#         # set ukuran kertas, 9 artinya kertas A4
#         sheet.set_paper(9)
#         # set margin kertas dalam satuan inchi
#         # sheet.set_margins(2,2,2,2)

#         # set lebar kolom
#         # sheet.set_column('B:B',0,0,{'hidden': True})
#         sheet.set_column('A:B', 50)
#         sheet.set_column('C:Z', 15)
        
#         row = 1
#         sheet.write(f'A{row}', 'NERACA', title_style)
#         row += 1
#         periode = f"{wizard_id.date_to.strftime('%m')} - {wizard_id.date_to.strftime('%Y')}"
#         sheet.write(f'A{row}', f"""Periode : {periode}""", title_style)
#         row += 3
#         sheet.write(f'A{row}', 'KODE', header_style)
#         sheet.write(f'B{row}', 'NAMA PERKIRAAN', header_style)
#         sheet.write(f'C{row}', 'KONSOLIDASI', header_style)
#         colhead = 3
#         branchs = wizard_id.get_list_branch()
#         for branch in branchs:
#             sheet.write(row - 1, colhead, branch['name'], header_style)
#             colhead += 1
#         row += 1


#         account_lines = wizard_id.compute_formula(wizard_id.date_from, wizard_id.date_to)
#         for account in account_lines:
#             text_style = workbook.add_format({'bold': False, 'align': 'left'})
#             float_style = workbook.add_format({'bold': False, 'align': 'right', 'num_format': '#,##0.00'})
#             if account.get('bold'):
#                 text_style = workbook.add_format({'bold': True, 'align': 'left'})
#                 float_style = workbook.add_format({'bold': True, 'align': 'right', 'num_format': '#,##0.00'})
#             if account.get('blank'):
#                 float_style = workbook.add_format({'color': 'white'})
            
#             # Check if the account name is a code followed by a name
#             account_name_parts = account['name'].split(' ', 1)
#             if len(account_name_parts) == 2 and account_name_parts[0].isdigit():
#                 account_code = account_name_parts[0]  # The first part is the code
#                 account_name = account_name_parts[1]  # The second part is the name
#             else:
#                 account_code = ''  # No code, so leave this empty
#                 account_name = account['name']  # Use the full string as the name
                    
#             # Write to Excel sheet
#             sheet.write(f'A{row}', account_code, text_style)
#             sheet.write(f'B{row}', account_name, text_style)            
#             sheet.write(f'C{row}', account['balance'], float_style)
            
#             # Initialize the starting column for branch balances
#             colbody = 3
            
#             for branch in account['branch_list_vals']:
#                 sheet.write(row - 1, colbody, branch['balance'], float_style)
#                 colbody += 1
            
#             row += 1
        
#         workbook.close()
#         output.seek(0)
#         response.stream.write(output.read())
#         output.close()
 
#         return response



# Andro version
class NeracaController(http.Controller):
    @http.route([
        '/neraca/export/<model("neraca.mb.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_neraca(self, wizard_id=False, **args):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Styles
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'left'})
        header_style = workbook.add_format({'bottom': 2, 'align': 'center'})
        text_style = workbook.add_format({'align': 'left'})
        float_style = workbook.add_format({'align': 'right', 'num_format': '#,##0.00'})

        # Create sheet
        sheet = workbook.add_worksheet()
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_column('A:B', 50)
        sheet.set_column('C:Z', 15)

        # Title & Period
        row = 1
        sheet.write(row, 0, 'NERACA', title_style)
        row += 1
        periode = f"{wizard_id.date_to.strftime('%m')} - {wizard_id.date_to.strftime('%Y')}"
        sheet.write(row, 0, f"Periode: {periode}", title_style)
        row += 3

        # Header
        headers = ['KODE', 'NAMA PERKIRAAN', 'KONSOLIDASI']
        branchs = wizard_id.get_list_branch()
        headers.extend([branch['name'] for branch in branchs])

        # Write headers in a single call
        sheet.write_row(row, 0, headers, header_style)
        row += 1

        # Fetch account data in a memory-efficient way
        for account in wizard_id.compute_formula(wizard_id.date_from, wizard_id.date_to):
            account_code, account_name = '', account['name']
            account_name_parts = account['name'].split(' ', 1)
            if len(account_name_parts) == 2 and account_name_parts[0].isdigit():
                account_code, account_name = account_name_parts

            row_values = [account_code, account_name, account['balance']]
            row_values.extend(branch['balance'] for branch in account['branch_list_vals'])

            # Use write_row() for efficiency
            sheet.write_row(row, 0, row_values, text_style if not account.get('bold') else workbook.add_format({'bold': True, 'align': 'left'}))
            row += 1

        # Close and return response
        workbook.close()
        output.seek(0)

        response = request.make_response(output.read(), headers=[
            ('Content-Type', 'application/vnd.ms-excel'),
            ('Content-Disposition', content_disposition('NERACA.xlsx')),
        ])
        return response


    # def get_value_pusat(self, account_id, report):
    #     where = """where am.state = 'posted' and aml.branch_id is null"""
    #     if account_id:
    #         where += f""" and aa.id = {account_id}"""
    #     if report.type == 'accounts':
    #         where += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
    #     if report.type == 'account_type':
    #         where += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""

    #     query = f"""
    #         select COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
    #         from account_move_line aml
    #         join account_move am on aml.move_id = am.id
    #         join account_account aa on aml.account_id = aa.id
    #         {where}
    #     """
    #     request._cr.execute(query)
    #     result = request._cr.dictfetchall()[0]
    #     return result
    
    
    
    # def get_value_multi_branch(self, account_id, report, branch_id, date_from, date_to):
    #     where = f"""where am.state = 'posted' and aml.date >= '{date_from}' and aml.date <= '{date_to}'"""
    #     if account_id:
    #         where += f""" and aa.id = {account_id}"""
    #     if branch_id:
    #         where += f""" and aml.branch_id = {branch_id}"""
    #     if report.type == 'accounts':
    #         where += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
    #     if report.type == 'account_type':
    #         where += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""

    #     query = f"""
    #         -- select COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
    #         select COALESCE(SUM(aml.balance), 0) as balance
    #         from account_move_line aml
    #         join account_move am on aml.move_id = am.id
    #         join account_account aa on aml.account_id = aa.id
    #         {where}
    #     """
    #     request._cr.execute(query)
    #     result = request._cr.dictfetchall()[0]
    #     return result



    # def get_value(self, wizard):
    #     periode = f"{wizard.date_to.strftime('%m')} - {wizard.date_to.strftime('%Y')}"
    #     account_report_id = wizard.account_report_id.id
    #     date_from = wizard.date_from
    #     date_to = wizard.date_to
        
        
    #     # GET BRANCH
    #     branchs = []
    #     request._cr.execute("""
    #         -- select COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
    #         select COALESCE(SUM(aml.balance), 0) as balance
    #         , aml.branch_id 
    #         from account_move_line aml
    #         group by aml.branch_id
    #     """)
    #     ress = request._cr.dictfetchall()
    #     if ress:
    #         branch_ids = [row['branch_id'] for row in ress]
    #         branchs = request.env['res.branch'].search([('id', 'in', branch_ids)], order="seq_id asc")


        
    #     # GET ACCOUNT LINE
    #     account_lines = []
    #     account_report = request.env['account.financial.report'].browse(account_report_id)
    #     child_reports = account_report._get_children_by_order()
    #     for report in child_reports:
    #         account_lines.append({
    #             'report': report,
    #             'account_id': False,
    #             'name1': report.name,
    #             'name2': '',
    #             'level': report.level,
    #             'balance': 0,
    #             'type': 'head',
    #         })

    #         # Start Detail Account
    #         account_sub_lines = []

    #         where_query = f"""where am.state = 'posted'"""
    #         if date_from:
    #             where_query += f""" and aml.date >= '{date_from}'"""
    #         if date_to:
    #             where_query += f""" and aml.date <= '{date_to}'"""
            
    #         if report.type == 'accounts':
    #             where_query += f""" and aa.id in {str(tuple(report.account_ids.ids)).replace(',)',')')}"""
    #         elif report.type == 'account_type':
    #             where_query += f""" and aa.account_type in {str(tuple(report.account_type_ids.mapped('type'))).replace(',)',')')}"""
    #         elif report.type == 'account_report' and report.account_report_id:
    #             continue
    #         elif report.type == 'sum':
    #             continue


    #         request._cr.execute(f"""
    #             select aa.id as account_id
    #                 , aa.code as account_code
    #                 , aa.name as account_name
    #                 , COALESCE(SUM(aml.debit), 0) - COALESCE(SUM(aml.credit), 0) as balance
    #             from account_move_line aml
    #             join account_move am on aml.move_id = am.id
    #             join account_account aa on aml.account_id = aa.id
    #             {where_query}
    #             group by 1,2,3
    #         """)
    #         total_balance = 0
    #         for row in request._cr.dictfetchall():
    #             account_name_value = list(row['account_name'].values())[0]
    #             account_sub_lines.append({
    #                 'report': report,
    #                 'account_id': row['account_id'],
    #                 'name1': row['account_code'],
    #                 'name2': account_name_value,
    #                 'level': report.level + 1,
    #                 'balance': row['balance'],
    #                 'type': 'subline',
    #             })
    #             total_balance += row['balance']
    #         account_sub_lines.append({
    #             'report': report,
    #             'account_id': False,
    #             'name1': '',
    #             'name2': 'JUMLAH' + ' ' + report.name,
    #             'level': report.level + 1,
    #             'balance': total_balance,
    #             'type': 'total',
    #         })
    #         account_lines += sorted(account_sub_lines, key=lambda account_sub_lines: account_sub_lines['name1'] and account_sub_lines['name2'])
        
        
    #     return {
    #         'periode': periode,
    #         'branchs': branchs,
    #         'account_lines': account_lines,
    #     }