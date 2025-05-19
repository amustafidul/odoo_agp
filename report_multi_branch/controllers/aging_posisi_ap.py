from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

import babel


class AgingPosisiAPController(http.Controller):
    @http.route([
        '/aging_posisi_ap/export/<model("aging.posisi.ap.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_aging_posisi_ap(self, wizard_id=False, **args):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('AGING POSISI AP.xlsx'))
            ]
        )

        # buat object workbook dari library xlsxwriter
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # buat style untuk mengatur jenis font, ukuran font, border dan alligment
        title_style = workbook.add_format({'font_size': 16, 'bold': True, 'align': 'center'})
        header_style_border = workbook.add_format({'bg_color': '#C6E0B4', 'bold': True, 'border': 1, 'align': 'center'})
        body_center_border = workbook.add_format({'border': 1, 'align': 'center'})
        body_left_border = workbook.add_format({'border': 1, 'align': 'left'})
        number_border = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'align': 'right'})

        sheet = workbook.add_worksheet()
        # set orientation jadi landscape
        sheet.set_landscape()
        # set ukuran kertas, 9 artinya kertas A4
        sheet.set_paper(9)
        # set margin kertas dalam satuan inchi
        # sheet.set_margins(2,2,2,2)

        # set lebar kolom
        # sheet.set_column('B:B',0,0,{'hidden': True})
        sheet.set_column('A:M', 20)

        row = 1
        col = 0
        sheet.merge_range(f'A{row}:I{row}', 'PT ADHI GUNA PUTERA', title_style)
        row += 1
        sheet.merge_range(f'A{row}:I{row}', 'LAPORAN POSISI PIUTANG', title_style)
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
        sheet.merge_range(f'A{row}:A{row + 1}', 'Jenis Piutang', header_style_border)
        sheet.merge_range(f'B{row}:B{row + 1}', 'Jumlah', header_style_border)
        sheet.merge_range(f'C{row}:H{row}', 'AGING', header_style_border)
        sheet.merge_range(f'I{row}:J{row}', 'Kelengkapan Berkas Penagihan', header_style_border)
        sheet.merge_range(f'K{row}:L{row}', 'Proses Penagihan', header_style_border)
        sheet.merge_range(f'M{row}:M{row + 1}', 'Keterangan', header_style_border)

        sheet.write(f'C{row + 1}', '1-2 Bulan', header_style_border)
        sheet.write(f'D{row + 1}', '3-6 Bulan', header_style_border)
        sheet.write(f'E{row + 1}', '7-9 Bulan', header_style_border)
        sheet.write(f'F{row + 1}', '10-12 Bulan', header_style_border)
        sheet.write(f'G{row + 1}', '1-3 Tahun', header_style_border)
        sheet.write(f'H{row + 1}', 'Lebih dari 3 Tahun', header_style_border)
        sheet.write(f'I{row + 1}', 'BAPP', header_style_border)
        sheet.write(f'J{row + 1}', 'BAST', header_style_border)
        sheet.write(f'K{row + 1}', 'Selesai', header_style_border)
        sheet.write(f'L{row + 1}', 'Belum Selesai', header_style_border)
        row += 2

        lines = []
        domain = [
            ('state', '=', 'posted'),
            ('move_type', '=', 'in_invoice'),
            ('payment_state', '!=', 'paid'),
        ]
        move = request.env['account.move'].search(domain)
        partner_ids = move.mapped('partner_id')
        no = 1
        for partner in partner_ids:
            total = sum(
                move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date <= wizard_id.periode).mapped(
                    'amount_residual'))
            total1 = sum(move.filtered(
                lambda x: x.partner_id.id == partner.id and x.invoice_date >= wizard_id.periode and x.invoice_date <= (
                            wizard_id.periode + relativedelta(months=6))).mapped('amount_residual'))
            total2 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        wizard_id.periode + relativedelta(months=7)) and x.invoice <= (
                                                             wizard_id.periode + relativedelta(months=12))).mapped(
                'amount_residual'))
            total3 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        wizard_id.periode + relativedelta(months=13)) and x.invoice <= (
                                                             wizard_id.periode + relativedelta(months=24))).mapped(
                'amount_residual'))
            total4 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        wizard_id.periode + relativedelta(months=25)) and x.invoice <= (
                                                             wizard_id.periode + relativedelta(months=36))).mapped(
                'amount_residual'))
            total5 = sum(move.filtered(lambda x: x.partner_id.id == partner.id and x.invoice_date >= (
                        wizard_id.periode + relativedelta(months=36))).mapped('amount_residual'))
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

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response