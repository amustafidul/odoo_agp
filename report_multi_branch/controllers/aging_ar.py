from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

import babel


class AgingARController(http.Controller):
    @http.route([
        '/aging_ar/export/<model("aging.ar.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_aging_ar(self, wizard_id=False, **args):
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
        jenis_kegiatan = res[wizard_id.jenis_kegiatan].upper() if wizard_id.jenis_kegiatan else ''
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(f'AGING PIUTANG {jenis_kegiatan}.xlsx'))
                    ]
                )
        
        # buat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # buat style untuk mengatur jenis font, ukuran font, border dan alligment
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'bg_color': '#ff6347', 'bold': True, 'border': 1, 'align': 'center'})
        body_center_border = workbook.add_format({'border': 1, 'align': 'center'})
        body_left_border = workbook.add_format({'border': 1, 'align': 'left'})
        number_border = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'right'})

        sheet = workbook.add_worksheet()
        # set orientation jadi landscape
        sheet.set_landscape()
        # set ukuran kertas, 9 artinya kertas A4
        sheet.set_paper(9)
        # set margin kertas dalam satuan inchi
        # sheet.set_margins(2,2,2,2)

        # set lebar kolom
        # sheet.set_column('B:B',0,0,{'hidden': True})
        sheet.set_column('A:I', 20)
        
        row = 1
        col = 0
        
        
        sheet.merge_range(f'A{row}:I{row}', f'AGING PIUTANG {jenis_kegiatan}', title_style)
        row += 1
        periode = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(wizard_id.periode, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        )
        periode = periode.upper()
        sheet.merge_range(f'A{row}:I{row}', f'PER {periode}', title_style)
        row += 2
        sheet.merge_range(f'A{row}:A{row + 1}', 'NO', header_style_border)
        sheet.merge_range(f'B{row}:B{row + 1}', 'KODE DEBITUR', header_style_border)
        sheet.merge_range(f'C{row}:C{row + 1}', 'NAMA DEBITUR', header_style_border)
        sheet.write(f'D{row}', 'SALDO', header_style_border)
        sheet.merge_range(f'E{row}:I{row}', 'AGING', header_style_border)
        
        sheet.write(f'D{row + 1}', periode, header_style_border)
        sheet.write(f'E{row + 1}', '0-6 BULAN', header_style_border)
        sheet.write(f'F{row + 1}', '7-12 BULAN', header_style_border)
        sheet.write(f'G{row + 1}', '13-24 BULAN', header_style_border)
        sheet.write(f'H{row + 1}', '25-36 BULAN', header_style_border)
        sheet.write(f'I{row + 1}', '> 36 BULAN', header_style_border)
        row += 2

        lines = []
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '!=', 'paid'),
        ]
        
        if wizard_id.jenis_kegiatan:
            domain += [('jenis_kegiatan', '=', wizard_id.jenis_kegiatan)]
        
        account_move = request.env['account.move'].search(domain, order='partner_id')
        partner_ids = account_move.mapped('partner_id')
        no = 1
        for partner in partner_ids:
            total = total1 = total2 = total3 = total4 = total5 = 0.0
            
            move_partner = account_move.filtered(lambda x:x.partner_id.id == partner.id)
            total = sum(move_partner.mapped('amount_residual'))
            for move in move_partner:
                age = int(((wizard_id.periode - move.date).days / 365) * 12)
                if age < 6:
                    total1 += move.amount_residual
                elif age >= 7 and age <= 12:
                    total2 += move.amount_residual
                elif age >= 13 and age <= 24:
                    total3 += move.amount_residual
                elif age >= 25 and age <= 36:
                    total4 += move.amount_residual
                elif age > 37:
                    total5 += move.amount_residual
            
            
            sheet.write(f'A{row}', no, body_center_border)
            sheet.write(f'B{row}', partner.x_vendor_code or '', body_center_border)
            sheet.write(f'C{row}', partner.name, body_left_border)
            sheet.write(f'D{row}', total, number_border)
            sheet.write(f'E{row}', total1, number_border)
            sheet.write(f'F{row}', total2, number_border)
            sheet.write(f'G{row}', total3, number_border)
            sheet.write(f'H{row}', total4, number_border)
            sheet.write(f'I{row}', total5, number_border)
            no += 1
            row += 1


        domain_line = [
            '|',
            ('move_id', '=', False),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('date', '<=', wizard_id.periode),
            '&',
            ('account_id.name', 'not ilike', 'Pajak'),
            ('account_id.name', 'not ilike', 'VAT'),
            ('account_id.name', 'not ilike', 'PPN'),
            ('account_id.name', 'not ilike', 'PPn')
        ]

        if wizard_id.jenis_kegiatan:
            domain_line.append(('account_id.name', 'ilike', wizard_id.jenis_kegiatan))

        move_lines = request.env['account.move.line'].search(domain_line)

        lines_by_partner = {}

        for line in move_lines:
            partner_id = line.partner_id.id
            if partner_id not in lines_by_partner:
                lines_by_partner[partner_id] = {
                    'code': line.partner_id.x_vendor_code or '',
                    'name': line.partner_id.name or '',
                    'total': 0.0,
                    'total1': 0.0,
                    'total2': 0.0,
                    'total3': 0.0,
                    'total4': 0.0,
                    'total5': 0.0,
                }

            line_age_days = int((wizard_id.periode - line.date).days)

            lines_by_partner[partner_id]['total'] += line.amount_residual
            if line_age_days <= 180:
                lines_by_partner[partner_id]['total1'] += line.amount_residual
            elif 181 <= line_age_days <= 360:
                lines_by_partner[partner_id]['total2'] += line.amount_residual
            elif 361 <= line_age_days <= 720:
                lines_by_partner[partner_id]['total3'] += line.amount_residual
            elif 721 <= line_age_days <= 1080:
                lines_by_partner[partner_id]['total4'] += line.amount_residual
            elif line_age_days > 1080:
                lines_by_partner[partner_id]['total5'] += line.amount_residual

        for partner_data in lines_by_partner.values():
            sheet.write(f'A{row}', no, body_center_border)
            sheet.write(f'B{row}', partner_data['code'], body_center_border)
            sheet.write(f'C{row}', partner_data['name'], body_left_border)
            sheet.write(f'D{row}', partner_data['total'], number_border)
            sheet.write(f'E{row}', partner_data['total1'], number_border)
            sheet.write(f'F{row}', partner_data['total2'], number_border)
            sheet.write(f'G{row}', partner_data['total3'], number_border)
            sheet.write(f'H{row}', partner_data['total4'], number_border)
            sheet.write(f'I{row}', partner_data['total5'], number_border)
            no += 1
            row += 1

        
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response