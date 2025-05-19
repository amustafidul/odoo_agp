from odoo import models, fields, api, _


class OdooPayrollReport(models.AbstractModel):
    _name = 'report.odoo_payroll.report_odoo_payroll_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, lines):
        sheet = workbook.add_worksheet('TAD Payroll')

        # Header format
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'fg_color': '#DAE3F3',
            'border': 1
        })
        header_format_biaya_pembinaan = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })
        header_format_head = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })
        content_format = workbook.add_format({
            'align': 'left',
            'border': 1
        })
        number_format = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right',
            'border': 1
        })
        number_format_biaya_pembinaan = workbook.add_format({
            'num_format': '#,##0',
            'align': 'right'
        })
        header_total_format = workbook.add_format({
            'bold': True,
            'align': 'right',
            'valign': 'vcenter',
            'fg_color': '#DAE3F3',
            'border': 1
        })

        branch = self.env['res.branch'].search([('id','=',data['form'].get('branch_id'))], limit=1)

        sheet.merge_range('A2:N2', 'TENAGA ALIH DAYA', header_format_head)
        sheet.merge_range('A3:N3', 'PEKERJAAN ADMINISTRASI DAN OPERASIONAL LAINNYA', header_format_head)
        sheet.merge_range('A4:N4', branch.name, header_format_head)
        sheet.merge_range('A5:N5', 'Tahun 2025', header_format_head)

        # Merging cells untuk header
        sheet.merge_range('A7:A8', 'No', header_format)
        sheet.merge_range('B7:B8', 'Nama', header_format)
        sheet.merge_range('C7:C8', 'Fungsi', header_format)
        sheet.merge_range('D7:I7', 'Gaji Koefisien', header_format)
        sheet.write('D8', 'UMK 2025 (Rp)', header_format)
        sheet.write('E8', 'Koefisien', header_format)
        sheet.write('F8', 'Gaji Koefisien', header_format)
        sheet.write('G8', 'Tunjangan (Rp)', header_format)
        sheet.write('H8', 'Delta (Rp)', header_format)
        sheet.write('I8', 'Total Gaji (Rp)', header_format)
        sheet.merge_range('J7:L8', 'Biaya Pegawai', header_format)
        sheet.write('J8', 'BPJS (Rp)', header_format)
        sheet.write('K8', 'THR (Rp)', header_format)
        sheet.write('L8', 'Kompensasi (Rp)', header_format)
        sheet.merge_range('M7:M8', 'Total Biaya Per Bulan', header_format)
        sheet.merge_range('N7:N8', 'Total Biaya Per Tahun', header_format)
        sheet.merge_range('P7:P8', 'Biaya Pembinaan', header_format_biaya_pembinaan)

        # Set column widths for better visibility
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 35)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 15)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 28)
        sheet.set_column('N:N', 28)
        sheet.set_column('P:P', 25)

        rec_obj = self.env['odoo.payroll.master'].search([('date_from','>=',data['form'].get('date_from')),
                                                          ('date_to','<=',data['form'].get('date_to')),
                                                          ('employee_id.employment_type','=','tad')])

        total_sec_start_row = 0

        sub_total_per_bulan = 0
        sub_total_per_tahun = 0
        total_biaya_pembinaan = 0

        # Tulis data ke worksheet
        for row_num, line in enumerate(rec_obj, start=8):
            sheet.write(row_num, 0, row_num - 7, content_format)  # No
            sheet.write(row_num, 1, line.employee_id.name, content_format)  # Nama
            sheet.write(row_num, 2, line.jabatan_id.name if line.jabatan_id else '-', content_format)  # Fungsi
            sheet.write(row_num, 3, line.umk_id.umk_amount_to, number_format)  # UMK 2025
            sheet.write(row_num, 4, line.koefisien_tad, number_format)  # Koefisien
            sheet.write(row_num, 5, line.tunjangan_tad_amount, number_format)  # Gaji Koefisien
            sheet.write(row_num, 6, line.tunjangan_posisi_amount, number_format)  # Tunjangan (Rp)
            sheet.write(row_num, 7, line.delta_tad_amount, number_format)  # Delta (Rp)
            sheet.write(row_num, 8, line.tad_salary_amount_total, number_format)  # Total Gaji (Rp)
            sheet.write(row_num, 9, line.tad_bpjs_jht_amount, number_format)  # BPJS (Rp)
            sheet.write(row_num, 10, line.tad_thr_amount, number_format)  # THR (Rp)
            sheet.write(row_num, 11, line.tad_kompensasi_amount, number_format)  # Kompensasi (Rp)
            total_biaya_per_bulan = (line.tad_salary_amount_total / line.tad_kompensasi_amount) if line.tad_kompensasi_amount != 0 \
                else line.tad_salary_amount_total
            total_biaya_per_tahun = total_biaya_per_bulan * 12
            sub_total_per_bulan += total_biaya_per_bulan
            sub_total_per_tahun += total_biaya_per_tahun
            sheet.write(row_num, 12, total_biaya_per_bulan, number_format)  # Total Biaya Per Bulan
            sheet.write(row_num, 13, total_biaya_per_tahun, number_format)  # Total Biaya Per Tahun
            sheet.write(row_num, 15, 35000, number_format_biaya_pembinaan)  # Total Biaya Per Tahun
            total_biaya_pembinaan += 35000
            total_sec_start_row = row_num + 2

        sheet.merge_range(f'A{total_sec_start_row}:L{total_sec_start_row}', 'SUB TOTAL', header_total_format)
        sheet.write(f'M{total_sec_start_row}', sub_total_per_bulan, number_format)
        sheet.write(f'N{total_sec_start_row}', sub_total_per_tahun, number_format)
        sheet.write(f'P{total_sec_start_row}', total_biaya_pembinaan, number_format_biaya_pembinaan)
        sheet.merge_range(f'A{total_sec_start_row + 1}:L{total_sec_start_row + 1}', 'MANAGEMENT FEE 8%', header_total_format)
        sheet.write(f'M{total_sec_start_row + 1}', (sub_total_per_bulan * 8) / 100, number_format)
        sheet.write(f'N{total_sec_start_row + 1}', (sub_total_per_tahun * 8) / 100, number_format)
        sheet.merge_range(f'A{total_sec_start_row + 2}:L{total_sec_start_row + 2}', 'PEMBINAAN TENAGA KERJA',
                          header_total_format)
        sheet.write(f'M{total_sec_start_row + 2}', total_biaya_pembinaan, number_format)
        sheet.write(f'N{total_sec_start_row + 2}', total_biaya_pembinaan * 12, number_format)
        sheet.merge_range(f'A{total_sec_start_row + 3}:L{total_sec_start_row + 3}', 'DASAR PENGENAAN PAJAK (DPP)',
                          header_total_format)
        sheet.write(f'M{total_sec_start_row + 3}', sub_total_per_bulan / total_biaya_pembinaan if total_biaya_pembinaan != 0 else 0, number_format)
        sheet.write(f'N{total_sec_start_row + 3}', sub_total_per_tahun / (total_biaya_pembinaan * 12) if total_biaya_pembinaan != 0 else 0, number_format)