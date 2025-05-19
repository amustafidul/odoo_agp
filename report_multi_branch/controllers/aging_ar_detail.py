from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter
import babel

class AgingARDetailController(http.Controller):
    @http.route([
        '/aging_ar_detail/export/<model("aging.ar.detail.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_aging_ar_detail(self, wizard_id=False, **args):
        res = {}
        mapping = [
            ('emkl', 'EMKL'),
            ('bongkar_muat', 'Bongkar Muat'),
            ('keagenan', 'Keagenan'),
            ('assist_tug', 'Assist Tug'),
            ('jetty_manajemen', 'Jetty Manajemen'),
            ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
            ('logistik', 'Logistik')
        ]
        for key, value in dict(mapping).items():
            res[key] = value
        
        jenis_kegiatan = res.get(wizard_id.jenis_kegiatan, '').upper()
        partner_name = wizard_id.partner_id.name if wizard_id.partner_id else ''

        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(f'AGING PIUTANG {jenis_kegiatan}.xlsx'))
                    ]
                )
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'bg_color': '#ff6347', 'bold': True, 'border': 1, 'align': 'center'})
        body_center_border = workbook.add_format({'border': 1, 'align': 'center'})
        body_left_border = workbook.add_format({'border': 1, 'align': 'left'})
        number_border = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'right'})

        sheet = workbook.add_worksheet()
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_column('A:N', 20)
        
        row = 1
        
        sheet.merge_range(f'A{row}:N{row}', f'AGING PIUTANG ASSIST {jenis_kegiatan}', title_style)
        row += 1
        periode = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(wizard_id.periode, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        ).upper()

        sheet.merge_range(f'A{row}:N{row}', f'PER {periode}', title_style)
        row += 2
        
        # Write headers
        sheet.write(f'A{row + 1}', 'NO', header_style_border)
        sheet.write(f'B{row + 1}', 'CABANG', header_style_border)
        sheet.write(f'C{row + 1}', 'NAMA DEBITUR', header_style_border)
        sheet.write(f'D{row + 1}', 'NO DOKUMEN', header_style_border)
        sheet.write(f'E{row + 1}', 'TANGGAL', header_style_border)
        sheet.write(f'F{row + 1}', 'JUMLAH HUTANG', header_style_border)
        sheet.write(f'G{row + 1}', 'DOKUMEN PELUNASAN', header_style_border)
        sheet.write(f'H{row + 1}', 'TANGGAL PEMBAYARAN', header_style_border)
        sheet.write(f'I{row + 1}', 'JUMLAH PEMBAYARAN', header_style_border)
        sheet.write(f'J{row + 1}', 'SALDO', header_style_border)
        sheet.write(f'K{row + 1}', 'UMUR (Hari)', header_style_border)
        sheet.write(f'L{row + 1}', 'KETERANGAN', header_style_border)
        sheet.write(f'M{row + 1}', '0-6 BULAN', header_style_border)
        sheet.write(f'N{row + 1}', '7-12 BULAN', header_style_border)
        sheet.write(f'O{row + 1}', '13-24 BULAN', header_style_border)
        sheet.write(f'P{row + 1}', '25-36 BULAN', header_style_border)
        sheet.write(f'Q{row + 1}', '> 36 BULAN', header_style_border)
        
        row += 2

        # Initialize row number for data
        no = 1

        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<=', wizard_id.periode),
            ('payment_state', '!=', 'paid'),
        ]
        
        if wizard_id.jenis_kegiatan:
            domain += [('jenis_kegiatan', '=', wizard_id.jenis_kegiatan)]
        if wizard_id.partner_id:
            domain += [('partner_id', '=', wizard_id.partner_id.id)]
        
        account_moves = request.env['account.move'].search(domain, order='date asc')
        partner_ids = account_moves.mapped('partner_id')
        
        for partner in partner_ids:
            move_partner = account_moves.filtered(lambda x: x.partner_id.id == partner.id)
            for move in move_partner:
                total = move.amount_residual
                total1 = total2 = total3 = total4 = total5 = 0.0

                age_id_days = int((wizard_id.periode - move.date).days)
                
                partial_reconciles = request.env['account.partial.reconcile'].search([
                    '|', ('debit_move_id.move_id', '=', move.id),
                    ('credit_move_id.move_id', '=', move.id),
                    ('create_date', '<=', wizard_id.periode)
                ])

                payment_ids = partial_reconciles.mapped('debit_move_id.move_id') + partial_reconciles.mapped('credit_move_id.move_id')
                payments = request.env['account.payment'].search([('move_id', 'in', payment_ids.ids), ('date', '<=', wizard_id.periode)])
                
                # Calculate the residual amount considering the payments up to the selected period
                residual_amount = move.amount_total - sum(payments.mapped('amount'))

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

                payment_names = ', '.join(payment.name for payment in payments)
                payment_amounts = sum(payment.amount for payment in payments)
                payment_dates = ', '.join(payment.date.strftime('%d/%m/%Y') for payment in payments)

                sheet.write(f'A{row}', no, body_center_border)
                sheet.write(f'B{row}', move.branch_id.name, body_center_border)
                sheet.write(f'C{row}', partner.name, body_left_border)
                sheet.write(f'D{row}', move.name, body_left_border)
                sheet.write(f'E{row}', move.date.strftime('%d/%m/%Y') or '', body_center_border)
                sheet.write(f'F{row}', move.amount_total, number_border)
                sheet.write(f'G{row}', payment_names, body_left_border)
                sheet.write(f'H{row}', payment_dates or '', body_center_border)
                sheet.write(f'I{row}', payment_amounts, number_border)                
                sheet.write(f'J{row}', residual_amount, number_border)
                sheet.write(f'K{row}', age_id_days, body_center_border)
                sheet.write(f'L{row}', move.narration or '', body_left_border)
                sheet.write(f'M{row}', total1, number_border)
                sheet.write(f'N{row}', total2, number_border)
                sheet.write(f'O{row}', total3, number_border)
                sheet.write(f'P{row}', total4, number_border)
                sheet.write(f'Q{row}', total5, number_border)
                no += 1
                row += 1

        # Proses data dari account.move.line yang tidak memiliki move_id
        domain_line = [
            '|',
            # ('move_id', '!=', move.id),
            ('move_id', '=', False),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('date', '<=', wizard_id.periode),
            '&',  # Kondisi AND untuk pengecualian nama-nama akun
            ('account_id.name', 'not ilike', 'Pajak'),
            ('account_id.name', 'not ilike', 'VAT'),
            ('account_id.name', 'not ilike', 'PPN'),
            ('account_id.name', 'not ilike', 'PPn')
        ]

        # Tambahkan filter untuk partner_id jika diisi
        if wizard_id.partner_id:
            domain_line.append(('partner_id', '=', wizard_id.partner_id.id))

        # Tambahkan filter untuk jenis_kegiatan jika diisi
        if wizard_id.jenis_kegiatan:
            domain_line.append(('account_id.name', 'ilike', wizard_id.jenis_kegiatan))

        move_lines = request.env['account.move.line'].search(domain_line)
        
        for line in move_lines:
            line_total1 = line_total2 = line_total3 = line_total4 = line_total5 = 0.0

            line_age_id_days = int((wizard_id.periode - line.date).days)
                
            if line_age_id_days <= 180:
                line_total1 = line.amount_residual
            elif 181 <= line_age_id_days <= 360:
                line_total2 = line.amount_residual
            elif 361 <= line_age_id_days <= 720:
                line_total3 = line.amount_residual
            elif 721 <= line_age_id_days <= 1080:
                line_total4 = line.amount_residual
            elif line_age_id_days > 1080:
                line_total5 = line.amount_residual

            sheet.write(f'A{row}', no, body_center_border)
            sheet.write(f'B{row}', line.branch_id.name, body_center_border)
            sheet.write(f'C{row}', line.partner_id.name, body_left_border)
            sheet.write(f'D{row}', line.name, body_left_border)
            sheet.write(f'E{row}', line.date.strftime('%d/%m/%Y') or '', body_center_border)
            sheet.write(f'F{row}', '0', number_border)
            sheet.write(f'G{row}', '', body_left_border)
            sheet.write(f'H{row}', '', body_left_border)
            sheet.write(f'I{row}', '0', number_border)                
            sheet.write(f'J{row}', line.amount_residual, number_border)
            sheet.write(f'K{row}', line_age_id_days, body_center_border)
            sheet.write(f'L{row}', '', body_left_border)
            sheet.write(f'M{row}', line_total1, number_border)
            sheet.write(f'N{row}', line_total2, number_border)
            sheet.write(f'O{row}', line_total3, number_border)
            sheet.write(f'P{row}', line_total3, number_border)
            sheet.write(f'Q{row}', line_total5, number_border)
            no += 1
            row += 1
        

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response
