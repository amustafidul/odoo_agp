from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

import babel


class HutangPiutangController(http.Controller):
    @http.route([
        '/hutang_piutang/export/<model("hutang.piutang.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_kartu_hutang(self, wizard_id=False, **args):
        wizard = request.env['hutang.piutang.wizard'].browse(int(wizard_id))

        # Initialize variables
        jenis_kartu = wizard.jenis_kartu.upper()
        jenis_kegiatan = dict([
            ('emkl', 'EMKL'),
            ('bongkar_muat', 'Bongkar Muat'),
            ('keagenan', 'Keagenan'),
            ('assist_tug', 'Assist Tug'),
            ('jetty_manajemen', 'Jetty Manajemen'),
            ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
            ('logistik', 'Logistik')
        ]).get(wizard.jenis_kegiatan, '').upper()
        
        # Set header strings
        str_kop = f'LISTING ACCOUNT {"RECEIVABLE / PIUTANG" if wizard.jenis_kartu == "piutang" else "PAYABLE / HUTANG"} {jenis_kegiatan}'
        str_title = f'AGING {"PIUTANG" if wizard.jenis_kartu == "piutang" else "HUTANG"} {jenis_kegiatan}'
        str_kode = 'KODE DEBITUR' if wizard.jenis_kartu == 'piutang' else 'KODE KREDITUR'
        str_nama = 'NAMA DEBITUR' if wizard.jenis_kartu == 'piutang' else 'NAMA KREDITUR'

        # Format period
        periode = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(wizard.periode, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        ).upper()

        # Create Excel workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        formats = self._initialize_formats(workbook)

        # Create initial sheets
        # sheet = workbook.add_worksheet('Aging')
        # sheet_rekap = workbook.add_worksheet('Rekap')
        # self._setup_sheet(sheet, 'I')
        # self._setup_sheet(sheet_rekap, 'D')

        # row = 1
        # sheet.write(f'A{row}', 'PT. ADHI GUNA PUTERA', formats['kop_style'])
        # sheet_rekap.write(f'A{row}', 'PT. ADHI GUNA PUTERA', formats['kop_style'])
        # row += 1
        # sheet.write(f'A{row}', str_kop, formats['kop_style'])
        # sheet_rekap.write(f'A{row}', str_kop, formats['kop_style'])
        # row += 1
        # sheet.write(f'A{row}', '2101105', formats['kop_style'])
        # sheet_rekap.write(f'A{row}', '2101105', formats['kop_style'])  
        # row += 1

        # sheet.merge_range(f'A{row}:I{row}', str_title, formats['title_style'])
        # sheet_rekap.merge_range(f'A{row}:D{row}', str_title, formats['title_style'])
        # row += 1
        # sheet.merge_range(f'A{row}:I{row}', f'PER, {periode}', formats['title_style'])
        # sheet_rekap.merge_range(f'A{row}:D{row}', f'PER, {periode}', formats['title_style'])
        # row += 2

        # sheet.merge_range(f'A{row}:A{row + 1}', 'NO', formats['header_style_border'])
        # sheet_rekap.merge_range(f'A{row}:A{row + 1}', 'NO', formats['header_style_border'])
        # sheet.merge_range(f'B{row}:B{row + 1}', str_kode, formats['header_style_border'])
        # sheet_rekap.merge_range(f'B{row}:B{row + 1}', str_kode, formats['header_style_border'])
        # sheet.merge_range(f'C{row}:C{row + 1}', str_nama, formats['header_style_border'])
        # sheet_rekap.merge_range(f'C{row}:C{row + 1}', str_nama, formats['header_style_border'])
        # sheet.write(f'D{row}', 'SALDO', formats['header_style_border'])
        # sheet_rekap.merge_range(f'D{row}:D{row + 1}', 'SALDO', formats['header_style_border'])
        # sheet.merge_range(f'E{row}:I{row}', 'AGING', formats['header_style_border'])

        # row += 1
        # sheet.write(f'D{row}', periode, formats['header_style_border'])
        # aging_headers = ['0-6 BULAN', '7-12 BULAN', '13-24 BULAN', '25-36 BULAN', '> 36 BULAN']
        # for col, header in enumerate(aging_headers, start=1):
        #     sheet.write(f'{chr(68 + col)}{row}', header, formats['header_style_border'])
        # row += 1

        # Prepare data
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice' if wizard.jenis_kartu == 'piutang' else 'in_invoice'),
            ('payment_state', '!=', 'paid'),
        ]
        if wizard.partner_ids:
            domain += [('partner_id', 'in', wizard.partner_ids.ids)]
        
        account_moves = request.env['account.move'].search(domain, order='partner_id')
        partner_ids = wizard.partner_ids or account_moves.mapped('partner_id')

        # Write data to sheets
        # no = 1
        for partner in partner_ids:
            # self._write_partner_data(workbook, sheet, sheet_rekap, formats, wizard, partner, account_moves, no, row, str_kop, str_title, str_nama, periode)
            self._write_partner_data(workbook, formats, wizard, partner, account_moves, str_kop, str_nama, periode)
            # no += 1
            # row += 1

        # Close workbook and return response
        workbook.close()
        output.seek(0)

        return self._prepare_response(output, f'KARTU {jenis_kartu} {jenis_kegiatan}.xlsx')

    def _initialize_formats(self, workbook):
        return {
            'kop_style': workbook.add_format({'font_size': 9, 'bold': True, 'align': 'left'}),
            'title_style': workbook.add_format({'font_size': 10, 'bold': True, 'align': 'center'}),
            'header_style_border': workbook.add_format({'font_size': 9, 'color': 'white', 'bg_color': '#FF3300', 'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'}),
            'body_center_border': workbook.add_format({'border': 1, 'align': 'center'}),
            'body_left_border': workbook.add_format({'border': 1, 'align': 'left'}),
            'number_border': workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'align': 'right'}),
            'footer_style_border': workbook.add_format({'num_format': '#,##0.00', 'font_size': 9, 'color': 'white', 'bg_color': '#2F75B5', 'bold': True, 'border': 1, 'align': 'right', 'valign': 'vcenter'})
        }

    # def _setup_sheet(self, sheet, last_column):
    #     sheet.set_column('A:A', 6)
    #     sheet.set_column('B:B', 14)
    #     sheet.set_column('C:C', 50)
    #     sheet.set_column(f'D:{last_column}', 15)

    # def _write_partner_data(self, workbook, sheet, sheet_rekap, formats, wizard, partner, account_moves, no, row, str_kop, str_title, str_nama, periode):
    def _write_partner_data(self, workbook, formats, wizard, partner, account_moves, str_kop, str_nama, periode):
        # row = sheet.dim_rowmax + 1
        move_partner = account_moves.filtered(lambda x: x.partner_id.id == partner.id)

        total, totals = self._calculate_aging_totals(move_partner, wizard.periode)
        
        # Write data to Aging sheet
        # sheet.write(f'A{row}', no, formats['body_center_border'])
        # sheet_rekap.write(f'A{row}', no, formats['body_center_border'])
        # sheet.write(f'B{row}', partner.x_vendor_code or '', formats['body_center_border'])
        # sheet_rekap.write(f'B{row}', partner.x_vendor_code or '', formats['body_center_border'])
        # sheet.write(f'C{row}', partner.name, formats['body_left_border'])
        # sheet_rekap.write(f'C{row}', partner.name, formats['body_left_border'])
        # sheet.write(f'D{row}', total, formats['number_border'])
        # sheet_rekap.write(f'D{row}', total, formats['number_border'])

        # for i, total_aging in enumerate(totals, start=1):
        #     sheet.write(f'{chr(68 + i)}{row}', total_aging, formats['number_border'])

        # Create a new sheet for each partner
        sheet_name = partner.name[:31]
        sheet_partner = workbook.add_worksheet(sheet_name)
        row = 1
        sheet_partner.merge_range(f'A{row}:Q{row}', str_kop, formats['title_style'])
        row += 1
        sheet_partner.merge_range(f'A{row}:Q{row}', f'PER, {periode}', formats['title_style'])
        row += 2
        
        if wizard.jenis_kartu == 'hutang':
            sheet_partner.set_column('A:A', 12)
            sheet_partner.set_column('B:D', 25)
            sheet_partner.set_column('E:K', 12)
            sheet_partner.set_column('L:L', 25)
            sheet_partner.set_column('M:Q', 12)

            row2 = row

            headers = ['CABANG', str_nama, 'NO INVOICE', 'NO TRANSAKSI', 'TANGGAL', 'JUMLAH HUTANG', 'PEMBAYARAN', 'NO TRANSAKSI', 'TANGGAL', 'SISA HUTANG', 'UP', 'KETERANGAN', '0 - 6 BULAN', '7 - 12 BULAN', '13 - 24 BULAN', '25 - 36 BULAN', '> 36 BULAN']
            for col, header in enumerate(headers):
                sheet_partner.write(f'{chr(65 + col)}{row2}', header, formats['header_style_border'])
            row2 += 1

            for move in move_partner:
                sheet_partner.write(f'A{row2}', move.branch_id.name or '', formats['body_left_border'])
                sheet_partner.write(f'B{row2}', move.partner_id.name, formats['body_left_border'])
                sheet_partner.write(f'C{row2}', move.name or '', formats['body_left_border'])
                sheet_partner.write(f'D{row2}', move.transaction_ids[0].name if move.transaction_ids else '', formats['body_left_border'])
                sheet_partner.write(f'E{row2}', move.date.strftime('%d/%m/%Y') or '', formats['body_center_border'])
                sheet_partner.write(f'F{row2}', move.amount_total or '', formats['number_border'])
                sheet_partner.write(f'G{row2}', move.payment_ids.mapped('amount') or '', formats['number_border'])
                sheet_partner.write(f'H{row2}', move.payment_ids.mapped('name') or '', formats['body_left_border'])
                sheet_partner.write(f'I{row2}', move.payment_ids.mapped('date') or '', formats['body_center_border'])
                sheet_partner.write(f'J{row2}', move.amount_residual or '', formats['number_border'])
                sheet_partner.write(f'K{row2}', '', formats['body_left_border'])
                sheet_partner.write(f'L{row2}', move.narration or '', formats['body_left_border'])
                for i, total_aging in enumerate(totals):
                    sheet_partner.write(f'{chr(77 + i)}{row2}', total_aging, formats['number_border'])
                row2 += 1
            row2 += 3
            sheet_partner.write(f'A{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'B{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'C{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'D{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'E{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'F{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'G{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'H{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'I{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'J{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'K{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'L{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'M{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'N{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'O{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'P{row2}', '', formats['footer_style_border'])
            sheet_partner.write(f'Q{row2}', '', formats['footer_style_border'])
            
        elif wizard.jenis_kartu == 'piutang':
            sheet_partner.set_column('A:A', 12)
            sheet_partner.set_column('B:D', 25)
            sheet_partner.set_column('E:I', 12)
            sheet_partner.set_column('J:J', 20)
            sheet_partner.set_column('K:T', 12)

            row3 = row

            headers = ['CABANG', str_nama, 'NO INVOICE', 'NO TRANSAKSI', 'TANGGAL', 'PIUTANG NETTO', 'PIUTANG RAGU2 TAHUN LALU', 'PIUTANG RAGU2 TAHUN 2016', 'PIUTANG BRUTO', 'NO TRANSAKSI', 'PELUNASAN', 'TANGGAL', 'SISA PIUTANG', 'UP', 'KETERANGAN', '0 - 6 BULAN', '7 - 12 BULAN', '13 - 24 BULAN', '25 - 36 BULAN', '> 36 BULAN']
            for col, header in enumerate(headers):
                sheet_partner.write(f'{chr(65 + col)}{row3}', header, formats['header_style_border'])
            row3 += 1

            for move in move_partner:
                sheet_partner.write(f'A{row3}', move.branch_id.name or '', formats['body_left_border'])
                sheet_partner.write(f'B{row3}', move.partner_id.name, formats['body_left_border'])
                sheet_partner.write(f'C{row3}', move.name or '', formats['body_left_border'])
                sheet_partner.write(f'D{row3}', move.transaction_ids[0].name if move.transaction_ids else '', formats['body_left_border'])
                sheet_partner.write(f'E{row3}', move.date.strftime('%d/%m/%Y') or '', formats['body_center_border'])
                sheet_partner.write(f'F{row3}', move.amount_total or '', formats['number_border'])
                sheet_partner.write(f'G{row3}', '', formats['number_border'])  
                sheet_partner.write(f'H{row3}', '', formats['number_border']) 
                sheet_partner.write(f'I{row3}', move.amount_total or '', formats['number_border'])  
                sheet_partner.write(f'J{row3}', ', '.join(move.payment_ids.mapped('name')) if move.payment_ids else '', formats['body_left_border'])
                sheet_partner.write(f'K{row3}', sum(move.payment_ids.mapped('amount')) if move.payment_ids else 0, formats['number_border'])
                sheet_partner.write(f'L{row3}', ', '.join(payment_date.strftime('%d/%m/%Y') for payment_date in move.payment_ids.mapped('date')) if move.payment_ids else '', formats['body_center_border'])
                sheet_partner.write(f'M{row3}', move.amount_residual or '', formats['number_border'])
                sheet_partner.write(f'N{row3}', '', formats['body_left_border'])
                sheet_partner.write(f'O{row3}', move.narration or '', formats['body_left_border'])
                for i, total_aging in enumerate(totals):
                    sheet_partner.write(f'{chr(80 + i)}{row3}', total_aging, formats['number_border'])
                row3 += 1
            row3 += 3
            sheet_partner.write(f'A{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'B{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'C{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'D{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'E{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'F{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'G{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'H{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'I{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'J{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'K{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'L{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'M{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'N{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'O{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'P{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'Q{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'R{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'S{row3}', '', formats['footer_style_border'])
            sheet_partner.write(f'T{row3}', '', formats['footer_style_border'])

    def _calculate_aging_totals(self, move_partner, periode):
        total = sum(move_partner.mapped('amount_residual'))
        totals = [0.0] * 5

        for move in move_partner:
            age = int(((periode - move.date).days / 365) * 12)
            if age < 6:
                totals[0] += move.amount_residual
            elif 7 <= age <= 12:
                totals[1] += move.amount_residual
            elif 13 <= age <= 24:
                totals[2] += move.amount_residual
            elif 25 <= age <= 36:
                totals[3] += move.amount_residual
            else:
                totals[4] += move.amount_residual

        return total, totals

    def _prepare_response(self, output, filename):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition(filename))
            ],
        )
        response.stream.write(output.read())
        output.close()
 
        return response
