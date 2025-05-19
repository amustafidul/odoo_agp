from odoo import _, api, fields, models, tools
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

import babel


class AgingPosisiARController(http.Controller):
    @http.route([
        '/aging_posisi_ar/export/<model("aging.posisi.ar.wizard"):wizard_id>',
    ], type='http', auth='user', csrf=False)
    def export_aging_posisi_ar(self, wizard_id=False, **args):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('AGING Posisi AR.xlsx'))
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
        sheet.merge_range(f'A{row}:H{row}', 'PT ADHI GUNA PUTERA', title_style)
        row += 1
        sheet.merge_range(f'A{row}:H{row}', 'LAPORAN POSISI PIUTANG', title_style)
        row += 1
        periode = tools.ustr(
            babel.dates.format_date(
                date=datetime.combine(wizard_id.periode, time.min),
                format="d MMMM y",
                locale="id_ID",
            )
        )
        periode = periode.upper()
        sheet.merge_range(f'A{row}:H{row}', f'PER {periode}', title_style)
        row += 2
        sheet.merge_range(f'A{row}:A{row + 1}', 'Jenis Piutang', header_style_border)
        sheet.merge_range(f'B{row}:B{row + 1}', 'Jumlah', header_style_border)
        sheet.merge_range(f'C{row}:H{row}', 'AGING', header_style_border)
        row += 1
        sheet.write(f'C{row}', '1-2 Bulan', header_style_border)
        sheet.write(f'D{row}', '3-6 Bulan', header_style_border)
        sheet.write(f'E{row}', '7-9 Bulan', header_style_border)
        sheet.write(f'F{row}', '10-12 Bulan', header_style_border)
        sheet.write(f'G{row}', '1-3 Tahun', header_style_border)
        sheet.write(f'H{row}', 'Lebih dari 3 Tahun', header_style_border)
        row += 1
        total = total1 = total2 = total3 = total4 = total5 = total6 = 0.0
        sheet.write(f'A{row}', 'Piutang Usaha :', body_left_border)
        sheet.write(f'B{row}', '', body_center_border)
        sheet.write(f'C{row}', '', body_center_border)
        sheet.write(f'D{row}', '', body_center_border)
        sheet.write(f'E{row}', '', body_center_border)
        sheet.write(f'F{row}', '', body_center_border)
        sheet.write(f'G{row}', '', body_center_border)
        sheet.write(f'H{row}', '', body_center_border)
        row += 1
        piutang_emkl = self.get_value(periode=wizard_id.periode, account_code=('1103201','1103301'))
        total += piutang_emkl['total']
        total1 += piutang_emkl['total1']
        total2 += piutang_emkl['total2']
        total3 += piutang_emkl['total3']
        total4 += piutang_emkl['total4']
        total5 += piutang_emkl['total5']
        total6 += piutang_emkl['total6']
        sheet.write(f'A{row}', '1. EMKL', body_left_border)
        sheet.write(f'B{row}', piutang_emkl['total'], number_border)
        sheet.write(f'C{row}', piutang_emkl['total1'], number_border)
        sheet.write(f'D{row}', piutang_emkl['total2'], number_border)
        sheet.write(f'E{row}', piutang_emkl['total3'], number_border)
        sheet.write(f'F{row}', piutang_emkl['total4'], number_border)
        sheet.write(f'G{row}', piutang_emkl['total5'], number_border)
        sheet.write(f'H{row}', piutang_emkl['total6'], number_border)
        row += 1
        piutang_bongkar_muat = self.get_value(periode=wizard_id.periode, account_code=('1103202','1103302'))
        total += piutang_bongkar_muat['total']
        total1 += piutang_bongkar_muat['total1']
        total2 += piutang_bongkar_muat['total2']
        total3 += piutang_bongkar_muat['total3']
        total4 += piutang_bongkar_muat['total4']
        total5 += piutang_bongkar_muat['total5']
        total6 += piutang_bongkar_muat['total6']
        sheet.write(f'A{row}', '2. Bongkar Muat', body_left_border)
        sheet.write(f'B{row}', piutang_bongkar_muat['total'], number_border)
        sheet.write(f'C{row}', piutang_bongkar_muat['total1'], number_border)
        sheet.write(f'D{row}', piutang_bongkar_muat['total2'], number_border)
        sheet.write(f'E{row}', piutang_bongkar_muat['total3'], number_border)
        sheet.write(f'F{row}', piutang_bongkar_muat['total4'], number_border)
        sheet.write(f'G{row}', piutang_bongkar_muat['total5'], number_border)
        sheet.write(f'H{row}', piutang_bongkar_muat['total6'], number_border)
        row += 1
        piutang_keagenan = self.get_value(periode=wizard_id.periode, account_code=('1103203','1103303'))
        total += piutang_keagenan['total']
        total1 += piutang_keagenan['total1']
        total2 += piutang_keagenan['total2']
        total3 += piutang_keagenan['total3']
        total4 += piutang_keagenan['total4']
        total5 += piutang_keagenan['total5']
        total6 += piutang_keagenan['total6']
        sheet.write(f'A{row}', '3. Keagenan', body_left_border)
        sheet.write(f'B{row}', piutang_keagenan['total'], number_border)
        sheet.write(f'C{row}', piutang_keagenan['total1'], number_border)
        sheet.write(f'D{row}', piutang_keagenan['total2'], number_border)
        sheet.write(f'E{row}', piutang_keagenan['total3'], number_border)
        sheet.write(f'F{row}', piutang_keagenan['total4'], number_border)
        sheet.write(f'G{row}', piutang_keagenan['total5'], number_border)
        sheet.write(f'H{row}', piutang_keagenan['total6'], number_border)
        row += 1
        piutang_assist_tug = self.get_value(periode=wizard_id.periode, account_code=('1103204','1103304'))
        total += piutang_assist_tug['total']
        total1 += piutang_assist_tug['total1']
        total2 += piutang_assist_tug['total2']
        total3 += piutang_assist_tug['total3']
        total4 += piutang_assist_tug['total4']
        total5 += piutang_assist_tug['total5']
        total6 += piutang_assist_tug['total6']
        sheet.write(f'A{row}', '4. Tug Assist', body_left_border)
        sheet.write(f'B{row}', piutang_assist_tug['total'], number_border)
        sheet.write(f'C{row}', piutang_assist_tug['total1'], number_border)
        sheet.write(f'D{row}', piutang_assist_tug['total2'], number_border)
        sheet.write(f'E{row}', piutang_assist_tug['total3'], number_border)
        sheet.write(f'F{row}', piutang_assist_tug['total4'], number_border)
        sheet.write(f'G{row}', piutang_assist_tug['total5'], number_border)
        sheet.write(f'H{row}', piutang_assist_tug['total6'], number_border)
        row += 1
        piutang_jetty_manajemen = self.get_value(periode=wizard_id.periode, account_code=('1103205','1103305'))
        total += piutang_jetty_manajemen['total']
        total1 += piutang_jetty_manajemen['total1']
        total2 += piutang_jetty_manajemen['total2']
        total3 += piutang_jetty_manajemen['total3']
        total4 += piutang_jetty_manajemen['total4']
        total5 += piutang_jetty_manajemen['total5']
        total6 += piutang_jetty_manajemen['total6']
        sheet.write(f'A{row}', '5. Jetty Manajemen', body_left_border)
        sheet.write(f'B{row}', piutang_jetty_manajemen['total'], number_border)
        sheet.write(f'C{row}', piutang_jetty_manajemen['total1'], number_border)
        sheet.write(f'D{row}', piutang_jetty_manajemen['total2'], number_border)
        sheet.write(f'E{row}', piutang_jetty_manajemen['total3'], number_border)
        sheet.write(f'F{row}', piutang_jetty_manajemen['total4'], number_border)
        sheet.write(f'G{row}', piutang_jetty_manajemen['total5'], number_border)
        sheet.write(f'H{row}', piutang_jetty_manajemen['total6'], number_border)
        row += 1
        piutang_jasa_operasi_lainnya = self.get_value(periode=wizard_id.periode, account_code=('1103206','1103306'))
        total += piutang_jasa_operasi_lainnya['total']
        total1 += piutang_jasa_operasi_lainnya['total1']
        total2 += piutang_jasa_operasi_lainnya['total2']
        total3 += piutang_jasa_operasi_lainnya['total3']
        total4 += piutang_jasa_operasi_lainnya['total4']
        total5 += piutang_jasa_operasi_lainnya['total5']
        total6 += piutang_jasa_operasi_lainnya['total6']
        sheet.write(f'A{row}', '6. Operasi Lainnya', body_left_border)
        sheet.write(f'B{row}', piutang_jasa_operasi_lainnya['total'], number_border)
        sheet.write(f'C{row}', piutang_jasa_operasi_lainnya['total1'], number_border)
        sheet.write(f'D{row}', piutang_jasa_operasi_lainnya['total2'], number_border)
        sheet.write(f'E{row}', piutang_jasa_operasi_lainnya['total3'], number_border)
        sheet.write(f'F{row}', piutang_jasa_operasi_lainnya['total4'], number_border)
        sheet.write(f'G{row}', piutang_jasa_operasi_lainnya['total5'], number_border)
        sheet.write(f'H{row}', piutang_jasa_operasi_lainnya['total6'], number_border)
        row += 1
        piutang_logistik = self.get_value(periode=wizard_id.periode, account_code=('1103207','1103307'))
        total += piutang_logistik['total']
        total1 += piutang_logistik['total1']
        total2 += piutang_logistik['total2']
        total3 += piutang_logistik['total3']
        total4 += piutang_logistik['total4']
        total5 += piutang_logistik['total5']
        total6 += piutang_logistik['total6']
        sheet.write(f'A{row}', '7. Logistik', body_left_border)
        sheet.write(f'B{row}', piutang_logistik['total'], number_border)
        sheet.write(f'C{row}', piutang_logistik['total1'], number_border)
        sheet.write(f'D{row}', piutang_logistik['total2'], number_border)
        sheet.write(f'E{row}', piutang_logistik['total3'], number_border)
        sheet.write(f'F{row}', piutang_logistik['total4'], number_border)
        sheet.write(f'G{row}', piutang_logistik['total5'], number_border)
        sheet.write(f'H{row}', piutang_logistik['total6'], number_border)
        row += 1
        piutang_lain = self.get_value(periode=wizard_id.periode, account_code=('1103701','1103702','1103703','1103704','1103401','1103402','1103403','1103404','1103499'))
        # piutang_lain = self.get_value(periode=wizard_id.periode, account_code=('1103701','1103702','1103703','1103704','1103401','1103402','1103403','1103404','1103499'))
        total += piutang_lain['total']
        total1 += piutang_lain['total1']
        total2 += piutang_lain['total2']
        total3 += piutang_lain['total3']
        total4 += piutang_lain['total4']
        total5 += piutang_lain['total5']
        total6 += piutang_lain['total6']
        sheet.write(f'A{row}', 'Piutang Lain-lain :', body_left_border)
        sheet.write(f'B{row}', piutang_lain['total'], number_border)
        sheet.write(f'C{row}', piutang_lain['total1'], number_border)
        sheet.write(f'D{row}', piutang_lain['total2'], number_border)
        sheet.write(f'E{row}', piutang_lain['total3'], number_border)
        sheet.write(f'F{row}', piutang_lain['total4'], number_border)
        sheet.write(f'G{row}', piutang_lain['total5'], number_border)
        sheet.write(f'H{row}', piutang_lain['total6'], number_border)
        row += 1
        sheet.write(f'A{row}', 'Pendapatan Yang Akan Diterima : :', body_left_border)
        sheet.write(f'B{row}', '', body_center_border)
        sheet.write(f'C{row}', '', body_center_border)
        sheet.write(f'D{row}', '', body_center_border)
        sheet.write(f'E{row}', '', body_center_border)
        sheet.write(f'F{row}', '', body_center_border)
        sheet.write(f'G{row}', '', body_center_border)
        sheet.write(f'H{row}', '', body_center_border)
        pendapatan_emkl = self.get_value(periode=wizard_id.periode, account_code=('1107101','1107201'))
        total += pendapatan_emkl['total']
        total1 += pendapatan_emkl['total1']
        total2 += pendapatan_emkl['total2']
        total3 += pendapatan_emkl['total3']
        total4 += pendapatan_emkl['total4']
        total5 += pendapatan_emkl['total5']
        total6 += pendapatan_emkl['total6']
        sheet.write(f'A{row}', '1. EMKL', body_left_border)
        sheet.write(f'B{row}', pendapatan_emkl['total'], number_border)
        sheet.write(f'C{row}', pendapatan_emkl['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_emkl['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_emkl['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_emkl['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_emkl['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_emkl['total6'], number_border)
        row += 1
        pendapatan_bongkar_muat = self.get_value(periode=wizard_id.periode, account_code=('1107102','1107202'))
        total += pendapatan_bongkar_muat['total']
        total1 += pendapatan_bongkar_muat['total1']
        total2 += pendapatan_bongkar_muat['total2']
        total3 += pendapatan_bongkar_muat['total3']
        total4 += pendapatan_bongkar_muat['total4']
        total5 += pendapatan_bongkar_muat['total5']
        total6 += pendapatan_bongkar_muat['total6']
        sheet.write(f'A{row}', '2. Bongkar Muat', body_left_border)
        sheet.write(f'B{row}', pendapatan_bongkar_muat['total'], number_border)
        sheet.write(f'C{row}', pendapatan_bongkar_muat['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_bongkar_muat['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_bongkar_muat['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_bongkar_muat['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_bongkar_muat['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_bongkar_muat['total6'], number_border)
        row += 1
        pendapatan_keagenan = self.get_value(periode=wizard_id.periode, account_code=('1107103','1107203'))
        total += pendapatan_keagenan['total']
        total1 += pendapatan_keagenan['total1']
        total2 += pendapatan_keagenan['total2']
        total3 += pendapatan_keagenan['total3']
        total4 += pendapatan_keagenan['total4']
        total5 += pendapatan_keagenan['total5']
        total6 += pendapatan_keagenan['total6']
        sheet.write(f'A{row}', '3. Keagenan', body_left_border)
        sheet.write(f'B{row}', pendapatan_keagenan['total'], number_border)
        sheet.write(f'C{row}', pendapatan_keagenan['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_keagenan['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_keagenan['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_keagenan['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_keagenan['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_keagenan['total6'], number_border)
        row += 1
        pendapatan_assist_tug = self.get_value(periode=wizard_id.periode, account_code=('1107104','1107204'))
        total += pendapatan_assist_tug['total']
        total1 += pendapatan_assist_tug['total1']
        total2 += pendapatan_assist_tug['total2']
        total3 += pendapatan_assist_tug['total3']
        total4 += pendapatan_assist_tug['total4']
        total5 += pendapatan_assist_tug['total5']
        total6 += pendapatan_assist_tug['total6']
        sheet.write(f'A{row}', '4. Tug Assist', body_left_border)
        sheet.write(f'B{row}', pendapatan_assist_tug['total'], number_border)
        sheet.write(f'C{row}', pendapatan_assist_tug['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_assist_tug['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_assist_tug['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_assist_tug['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_assist_tug['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_assist_tug['total6'], number_border)
        row += 1
        pendapatan_jetty_manajemen = self.get_value(periode=wizard_id.periode, account_code=('1107105','1107205'))
        total += pendapatan_jetty_manajemen['total']
        total1 += pendapatan_jetty_manajemen['total1']
        total2 += pendapatan_jetty_manajemen['total2']
        total3 += pendapatan_jetty_manajemen['total3']
        total4 += pendapatan_jetty_manajemen['total4']
        total5 += pendapatan_jetty_manajemen['total5']
        total6 += pendapatan_jetty_manajemen['total6']
        sheet.write(f'A{row}', '5. Jetty Manajemen', body_left_border)
        sheet.write(f'B{row}', pendapatan_jetty_manajemen['total'], number_border)
        sheet.write(f'C{row}', pendapatan_jetty_manajemen['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_jetty_manajemen['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_jetty_manajemen['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_jetty_manajemen['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_jetty_manajemen['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_jetty_manajemen['total6'], number_border)
        row += 1
        pendapatan_jasa_operasi_lainnya = self.get_value(periode=wizard_id.periode, account_code=('1107106','1107206'))
        total += pendapatan_jasa_operasi_lainnya['total']
        total1 += pendapatan_jasa_operasi_lainnya['total1']
        total2 += pendapatan_jasa_operasi_lainnya['total2']
        total3 += pendapatan_jasa_operasi_lainnya['total3']
        total4 += pendapatan_jasa_operasi_lainnya['total4']
        total5 += pendapatan_jasa_operasi_lainnya['total5']
        total6 += pendapatan_jasa_operasi_lainnya['total6']
        sheet.write(f'A{row}', '6. Operasi Lainnya', body_left_border)
        sheet.write(f'B{row}', pendapatan_jasa_operasi_lainnya['total'], number_border)
        sheet.write(f'C{row}', pendapatan_jasa_operasi_lainnya['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_jasa_operasi_lainnya['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_jasa_operasi_lainnya['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_jasa_operasi_lainnya['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_jasa_operasi_lainnya['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_jasa_operasi_lainnya['total6'], number_border)
        row += 1
        pendapatan_logistik = self.get_value(periode=wizard_id.periode, account_code=('1107107','1107207'))
        total += pendapatan_logistik['total']
        total1 += pendapatan_logistik['total1']
        total2 += pendapatan_logistik['total2']
        total3 += pendapatan_logistik['total3']
        total4 += pendapatan_logistik['total4']
        total5 += pendapatan_logistik['total5']
        total6 += pendapatan_logistik['total6']
        sheet.write(f'A{row}', '7. Logistik', body_left_border)
        sheet.write(f'B{row}', pendapatan_logistik['total'], number_border)
        sheet.write(f'C{row}', pendapatan_logistik['total1'], number_border)
        sheet.write(f'D{row}', pendapatan_logistik['total2'], number_border)
        sheet.write(f'E{row}', pendapatan_logistik['total3'], number_border)
        sheet.write(f'F{row}', pendapatan_logistik['total4'], number_border)
        sheet.write(f'G{row}', pendapatan_logistik['total5'], number_border)
        sheet.write(f'H{row}', pendapatan_logistik['total6'], number_border)
        row += 1
        sheet.write(f'A{row}', 'Total Piutang', body_left_border)
        sheet.write(f'B{row}', total, number_border)
        sheet.write(f'C{row}', total1, number_border)
        sheet.write(f'D{row}', total2, number_border)
        sheet.write(f'E{row}', total3, number_border)
        sheet.write(f'F{row}', total4, number_border)
        sheet.write(f'G{row}', total5, number_border)
        sheet.write(f'H{row}', total6, number_border)

        

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response


    
    def get_value(self, periode=False, jenis_kegiatan=False, account_code=''):
        total = total1 = total2 = total3 = total4 = total5 = total6 = 0.0
        domain = [
            ('parent_state', '=', 'posted'),
            ('account_id.code', 'in', account_code),
        ]
        # if jenis_kegiatan:
        #     domain += [('jenis_kegiatan', '=', jenis_kegiatan)]
        move_line_obj = request.env['account.move.line'].search(domain)
        
        for move_line in move_line_obj:
            month = int(((periode - move_line.date).days / 365) * 12)
            years = int((periode - move_line.date).days / 365)
            total += move_line.balance
            if month >= 1 and month <= 2:
                total1 += move_line.balance
            elif month >= 3 and month <= 6:
                total2 += move_line.balance
            elif month >= 7 and month <= 9:
                total3 += move_line.balance
            elif month >= 10 and month <= 12:
                total4 += move_line.balance
            elif years >= 1 and years <= 3:
                total5 += move_line.balance
            elif years > 3:
                total6 += move_line.balance
        # return total, total1, total2, total3, total4, total5, total6

        return {
            'total': total,
            'total1': total1,
            'total2': total2,
            'total3': total3,
            'total4': total4,
            'total5': total5,
            'total6': total6,
        }