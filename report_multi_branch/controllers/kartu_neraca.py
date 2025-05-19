from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime

class KartuNeracaController(http.Controller):
    @http.route('/kartu_neraca/export/<model("kartu.neraca.wizard"):wizard_id>', type='http', auth='user', csrf=False)
    def export_kartu_neraca(self, wizard_id=None, **args):
        if not wizard_id:
            return request.not_found()

        # Prepare the data
        start_date = wizard_id.start_date
        end_date = wizard_id.end_date
        account_id = wizard_id.account_id
        account_code = account_id.code if account_id else ''
        account_name = account_id.name if account_id else ''
        report_type = wizard_id.report_type

        # Prepare the XLSX file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        # Define styles
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'bg_color': '#ff6347', 'bold': True, 'border': 1, 'align': 'center'})
        body_center_border = workbook.add_format({'border': 1, 'align': 'center'})
        body_left_border = workbook.add_format({'border': 1, 'align': 'left'})
        number_border = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'align': 'right'})

        # Set sheet options
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_column('A:Q', 20)

        # Write title and header
        row = 0
        sheet.merge_range(f'A{row + 1}:{"Q" if report_type == "detail" else "I"}{row + 1}', 'Kartu Neraca', title_style)
        row += 1
        sheet.merge_range(f'A{row + 1}:{"Q" if report_type == "detail" else "I"}{row + 1}', f'Periode {start_date} - {end_date}', title_style)
        row += 1
        sheet.merge_range(f'A{row + 1}:{"Q" if report_type == "detail" else "I"}{row + 1}', f'{account_code} - {account_name}', title_style)
        row += 2
        
        # Write headers
        if report_type == 'detail':
            headers = ['NO', 'CABANG', 'NAMA DEBITUR', 'NO DOKUMEN', 'TANGGAL', 'JUMLAH', 'DOKUMEN PELUNASAN', 'TANGGAL', 'PELUNASA', 'SALDO', 'UMUR (Hari)', 'KETERANGAN', '0-6 BULAN', '7-12 BULAN', '13-24 BULAN', '25-36 BULAN', '> 36 BULAN']
        elif report_type == 'summary':
            headers = ['NO', 'KODE DEBITUR', 'NAMA DEBITUR', 'SALDO', '0-6 BULAN', '7-12 BULAN', '13-24 BULAN', '25-36 BULAN', '> 36 BULAN']        
        
        # Write header row
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_style_border)
        row += 1

        # Initialize row number for data
        no = 1
        # Prepare domain for search
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ['in_invoice', 'out_invoice']),
            ('move_id.invoice_date_due', '<=', end_date),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ]      
        
        if wizard_id.partner_id:
            domain.append(('partner_id', '=', wizard_id.partner_id.id))
        if wizard_id.account_id:
            domain.append(('account_id', '=', wizard_id.account_id.id))
        if wizard_id.jenis_kegiatan:
            domain.append(('move_id.jenis_kegiatan', '=', wizard_id.jenis_kegiatan))

        # Fetch data
        move_lines = request.env['account.move.line'].search(domain)
        partners = move_lines.mapped('move_id.partner_id')

        if report_type == 'detail':
            no = 1
            for partner in partners:
                partner_lines = move_lines.filtered(lambda l: l.move_id.partner_id.id == partner.id)
                total = sum(partner_lines.mapped('balance'))
                for line in partner_lines:
                    move = line.move_id
                    age_id_days = int((wizard_id.end_date - move.date).days)

                    partial_reconciles = request.env['account.partial.reconcile'].search([
                        '|', ('debit_move_id.move_id', '=', move.id),
                        ('credit_move_id.move_id', '=', move.id),
                        ('create_date', '<=', end_date)
                    ])
                    
                    payment_ids = partial_reconciles.mapped('debit_move_id.move_id') + partial_reconciles.mapped('credit_move_id.move_id')
                    payments = request.env['account.payment'].search([('move_id', 'in', payment_ids.ids), ('date', '<=', end_date)])

                    residual_amount = line.balance - sum(payments.mapped('amount'))

                    payment_names = ', '.join(payment.name for payment in payments)
                    payment_amounts = sum(payment.amount for payment in payments)
                    payment_dates = ', '.join(payment.date.strftime('%d/%m/%Y') for payment in payments)

                    # Define totals
                    total1 = total2 = total3 = total4 = total5 = 0.0
                    if age_id_days <= 180:
                        total1 = residual_amount
                    elif 181 <= age_id_days <= 360:
                        total2 = residual_amount
                    elif 361 <= age_id_days <= 720:
                        total3 = residual_amount
                    elif 721 <= age_id_days <= 1080:
                        total4 = residual_amount
                    elif age_id_days > 1080:
                        total5 = residual_amount

                    
                    sheet.write(row, 0, no, body_center_border)
                    sheet.write(row, 1, move.branch_id.name or '', body_left_border)
                    sheet.write(row, 2, move.partner_id.name or '', body_left_border)
                    sheet.write(row, 3, move.name or '', body_left_border)
                    sheet.write(row, 4, move.date.strftime('%d/%m/%Y') or '', body_center_border)
                    sheet.write(row, 5, move.amount_total or 0.0, number_border)
                    sheet.write(row, 6, payment_names or '', body_left_border)
                    sheet.write(row, 7, payment_dates or '', body_center_border)
                    sheet.write(row, 8, payment_amounts or 0.0, number_border)
                    sheet.write(row, 9, residual_amount or 0.0, number_border)
                    sheet.write(row, 10, age_id_days or '', body_center_border)
                    sheet.write(row, 11, move.narration or '', body_left_border)
                    sheet.write(row, 12, total1, number_border)
                    sheet.write(row, 13, total2, number_border)
                    sheet.write(row, 14, total3, number_border)
                    sheet.write(row, 15, total4, number_border)
                    sheet.write(row, 16, total5, number_border)

                    row += 1
                    no += 1

        elif report_type == 'summary':
            no = 1
            for partner in partners:
                partner_lines = move_lines.filtered(lambda l: l.move_id.partner_id.id == partner.id)
                
                # Initialize totals
                total = sum(partner_lines.mapped('balance'))
                total1 = total2 = total3 = total4 = total5 = 0.0
                
                for line in partner_lines:
                    move = line.move_id
                    age_id_days = int((wizard_id.end_date - move.date).days)

                    if age_id_days <= 180:
                        total1 += line.balance
                    elif 181 <= age_id_days <= 360:
                        total2 += line.balance
                    elif 361 <= age_id_days <= 720:
                        total3 += line.balance
                    elif 721 <= age_id_days <= 1080:
                        total4 += line.balance
                    elif age_id_days > 1080:
                        total5 += line.balance

                # Write summary data to sheet
                sheet.write(row, 0, no, body_center_border)
                sheet.write(row, 1, partner.x_vendor_code or '', body_center_border)
                sheet.write(row, 2, partner.name or '', body_left_border)
                sheet.write(row, 3, total, number_border)
                sheet.write(row, 4, total1, number_border)
                sheet.write(row, 5, total2, number_border)
                sheet.write(row, 6, total3, number_border)
                sheet.write(row, 7, total4, number_border)
                sheet.write(row, 8, total5, number_border)

                no += 1
                row += 1

        # Close the workbook and get the value
        workbook.close()
        output.seek(0)
        file_data = output.read()

        # Create and return the response
        file_name = f"{account_code}_{account_name}_{start_date}_{end_date}_{report_type}.xlsx"
        return request.make_response(
            file_data,
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename="{file_name}"')
            ]
        )