from odoo import models, fields


class TnaRekapReportXlsx(models.AbstractModel):
    _name = 'report.agp_training_management.report_tna_rekap_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Laporan Rekapitulasi TNA XLSX'

    def generate_xlsx_report(self, workbook, data, wizard):
        period_id = wizard.period_id
        branch_ids = wizard.branch_ids
        department_ids = wizard.department_ids

        domain = [('period_id', '=', period_id.id)]
        if branch_ids:
            domain.append(('branch_id', 'in', branch_ids.ids))
        if department_ids:
            domain.append(('department_id', 'in', department_ids.ids))
        domain.append(('state', 'in', ['approved', 'realized']))

        proposed_trainings = self.env['tna.proposed.training'].search(
            domain,
            order='branch_id, department_id, name'
        )

        sheet = workbook.add_worksheet(f'Rekap TNA {period_id.name[:31]}') # Nama sheet maks 31 char
        bold_format = workbook.add_format({'bold': True})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#D3D3D3'})
        cell_format = workbook.add_format({'border': 1, 'valign': 'top'}) # Tambahkan valign
        currency_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'valign': 'top'})
        integer_format = workbook.add_format({'num_format': '#,##0', 'border': 1, 'valign': 'top'})
        total_header_format = workbook.add_format({'bold': True, 'border': 1, 'valign': 'top'}) # Untuk header total
        total_currency_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'border': 1, 'valign': 'top'})
        total_integer_format = workbook.add_format({'bold': True, 'num_format': '#,##0', 'border': 1, 'valign': 'top'})


        sheet.merge_range('A1:N1', f'Laporan Rekapitulasi Training Need Analysis (TNA) - Periode: {period_id.name}', bold_format)

        row_num = 3
        headers = [
            'No.', 'Cabang Pengusul', 'Divisi Pengusul', 'Nama Training Diusulkan', 'Lingkup Diklat',
            'Status Usulan', 'Total Estimasi Peserta',
            'Peserta Organik', 'Peserta TAD/PKWT',
            'Estimasi Biaya Organik', 'Estimasi Biaya TAD/PKWT', 'Total Estimasi Biaya',
            'Total Hari Organik (Man-days)', 'Total Hari TAD/PKWT (Man-days)'
        ]

        column_widths = [len(h) + 2 for h in headers]

        for col_num, header in enumerate(headers):
            sheet.write(row_num, col_num, header, header_format)
            # sheet.set_column(col_num, col_num, column_widths[col_num])

        row_num += 1
        no_urut = 1

        grand_total_peserta = 0
        grand_total_peserta_organik = 0
        grand_total_peserta_tad_pkwt = 0
        grand_total_biaya_organik = 0
        grand_total_biaya_tad_pkwt = 0
        grand_total_biaya = 0
        grand_total_hari_organik = 0
        grand_total_hari_tad_pkwt = 0

        data_to_write = []

        for pt in proposed_trainings:
            row_data = [
                no_urut,
                pt.branch_id.name or '-',
                pt.department_id.name or '-',
                pt.name or '-',
                pt.training_scope_id.name or '-',
                dict(pt._fields['state'].selection).get(pt.state, pt.state),
                pt.estimated_participant_count,
                pt.participants_for_rekap_organik,
                pt.participants_for_rekap_tad_pkwt,
                pt.cost_for_rekap_organik,
                pt.cost_for_rekap_tad_pkwt,
                pt.estimated_cost,
                pt.days_for_rekap_organik,
                pt.days_for_rekap_tad_pkwt
            ]
            data_to_write.append(row_data)

            grand_total_peserta += pt.estimated_participant_count
            grand_total_peserta_organik += pt.participants_for_rekap_organik
            grand_total_peserta_tad_pkwt += pt.participants_for_rekap_tad_pkwt
            grand_total_biaya_organik += pt.cost_for_rekap_organik
            grand_total_biaya_tad_pkwt += pt.cost_for_rekap_tad_pkwt
            grand_total_biaya += pt.estimated_cost
            grand_total_hari_organik += pt.days_for_rekap_organik
            grand_total_hari_tad_pkwt += pt.days_for_rekap_tad_pkwt
            no_urut += 1

        for r_idx, row_values in enumerate(data_to_write):
            for c_idx, value in enumerate(row_values):
                current_format = cell_format
                if isinstance(value, (int, float)):
                    if c_idx in [9, 10, 11]:
                        current_format = currency_format
                    else:
                        current_format = integer_format

                sheet.write(row_num + r_idx, c_idx, value, current_format)
                column_widths[c_idx] = max(column_widths[c_idx], len(str(value)) + 2)

        row_num += len(data_to_write)

        if proposed_trainings:
            sheet.merge_range(row_num, 0, row_num, 5, 'GRAND TOTAL', total_header_format)

            total_data = [
                grand_total_peserta, grand_total_peserta_organik, grand_total_peserta_tad_pkwt,
                grand_total_biaya_organik, grand_total_biaya_tad_pkwt, grand_total_biaya,
                grand_total_hari_organik, grand_total_hari_tad_pkwt
            ]
            total_formats = [
                total_integer_format, total_integer_format, total_integer_format,
                total_currency_format, total_currency_format, total_currency_format,
                total_integer_format, total_integer_format
            ]

            for c_idx, total_value in enumerate(total_data):
                sheet.write(row_num, c_idx + 6, total_value, total_formats[c_idx])
                column_widths[c_idx + 6] = max(column_widths[c_idx + 6], len(str(total_value)) + 2)


        for i, width in enumerate(column_widths):
            sheet.set_column(i, i, width)