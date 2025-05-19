import base64
import io
import calendar
import xlsxwriter
from datetime import date
from odoo import models, fields, api
from odoo.exceptions import UserError


class PayrollTadReportWizard(models.TransientModel):
    _name = 'payroll.tad.report.wizard'
    _description = 'TAD Payroll Report Wizard'

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: date.today()
    )
    hr_branch_id = fields.Many2one(
        'hr.branch',
        string='Cabang',
        help="Filter payslip berdasarkan cabang pegawai."
    )

    def action_print_excel(self):
        # Filter payslip sesuai kriteria
        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
            ('employee_id.hr_branch_id', '=', self.hr_branch_id.id),
        ])
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type and slip.employee_id.employment_type == 'tad'
        )

        # --- Mengumpulkan data dinamis untuk kolom report ---
        # category_lines_map: key = nama kategori,
        # value = dictionary: { rule_name: sequence }
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                # Ambil nilai sequence; default 0 jika tidak ada
                seq_val = line.sequence or 0
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    # Simpan nilai sequence terkecil jika rule muncul lebih dari satu
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], seq_val)
                else:
                    category_lines_map[cat_name][rule_name] = seq_val

        # Buat dictionary untuk menyimpan nilai minimal sequence per kategori
        category_sequence = {}
        # Ubah masing-masing nilai dictionary menjadi list rule yang sudah disortir berdasarkan sequence
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda r: r[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat] = [rule for rule, seq in sorted_rules]

        # Urutkan kategori berdasarkan nilai minimal sequence dari masing-masing kategori
        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        # --- Menyiapkan data untuk laporan Excel ---
        data_for_excel = []
        for slip in payslips:
            slip_data = {
                'nama': slip.employee_id.name or '',
                'fungsi': slip.employee_id.fungsi_penugasan_id.name or '',
                'slip_number': slip.number or '',
                'lines_by_cat': {},
            }
            for cat in sorted_categories:
                slip_data['lines_by_cat'][cat] = {}
                for rule_name in category_lines_map[cat]:
                    slip_data['lines_by_cat'][cat][rule_name] = 0.0
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                if cat_name in slip_data['lines_by_cat'] and rule_name in slip_data['lines_by_cat'][cat_name]:
                    slip_data['lines_by_cat'][cat_name][rule_name] += line.total
            data_for_excel.append(slip_data)

        year_str = str(self.date_to.year)
        branch_name = self.hr_branch_id.name or 'N/A'

        file_data = self._generate_excel_file(
            data_for_excel,
            category_lines_map,
            sorted_categories,
            branch_name,
            year_str
        )

        attachment = self.env['ir.attachment'].create({
            'name': 'Payroll_TAD_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }

    def _generate_excel_file(self, data_for_excel, category_lines_map, sorted_categories, branch_name, year_str):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Payroll TAD")

        # === Format Cells ===
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4472C4',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })

        top_header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
        })

        total_dynamic_cols = sum(len(category_lines_map[cat]) for cat in sorted_categories)
        total_static_cols = 3
        last_col_index = total_static_cols + total_dynamic_cols - 1

        sheet.merge_range(0, 0, 0, last_col_index, "RENCANA ANGGARAN BIAYA", top_header_format)
        sheet.merge_range(1, 0, 1, last_col_index, "TENAGA ALIH DAYA", top_header_format)
        sheet.merge_range(2, 0, 2, last_col_index, "PEKERJAAN ADMINISTRASI DAN OPERASIONAL LAINNYA", top_header_format)
        sheet.merge_range(3, 0, 3, last_col_index, f"PADA CABANG {branch_name}", top_header_format)
        sheet.merge_range(4, 0, 4, last_col_index, f"TAHUN {year_str}", top_header_format)

        static_headers = ["Nama", "Fungsi Penugasan", "Payslip Number"]
        for col, hdr in enumerate(static_headers):
            sheet.merge_range(6, col, 7, col, hdr, header_format)

        col_offset = len(static_headers)
        row_kategori = 6
        row_rules = 7

        # Buat header kolom dinamis berdasarkan kategori dan rule yang sudah diurutkan
        for cat in sorted_categories:
            rules_in_cat = category_lines_map[cat]
            num_rules = len(rules_in_cat)
            if num_rules == 1:
                sheet.write(row_kategori, col_offset, cat, header_format)
                sheet.write(row_rules, col_offset, rules_in_cat[0], header_format)
                col_offset += 1
            else:
                sheet.merge_range(row_kategori, col_offset, row_kategori, col_offset + num_rules - 1, cat, header_format)
                for idx, rule_name in enumerate(rules_in_cat):
                    sheet.write(row_rules, col_offset + idx, rule_name, header_format)
                col_offset += num_rules

        start_data_row = 8
        row = start_data_row
        col_widths = {}

        for col, hdr in enumerate(static_headers):
            col_widths[col] = len(hdr)

        col_dyn = len(static_headers)
        for cat in sorted_categories:
            for rule_name in category_lines_map[cat]:
                base_len = max(len(cat), len(rule_name))
                col_widths[col_dyn] = base_len
                col_dyn += 1

        for rec in data_for_excel:
            sheet.write(row, 0, rec['nama'], text_format)
            col_widths[0] = max(col_widths[0], len(str(rec['nama'] or '')))

            sheet.write(row, 1, rec['fungsi'], text_format)
            col_widths[1] = max(col_widths[1], len(str(rec['fungsi'] or '')))

            sheet.write(row, 2, rec['slip_number'], text_format)
            col_widths[2] = max(col_widths[2], len(str(rec['slip_number'] or '')))

            col_dyn = len(static_headers)
            for cat in sorted_categories:
                for rule_name in category_lines_map[cat]:
                    amount = rec['lines_by_cat'][cat][rule_name]
                    sheet.write_number(row, col_dyn, amount, currency_format)

                    amount_str = f"{int(amount):,}" if amount else "0"
                    col_widths[col_dyn] = max(col_widths[col_dyn], len(amount_str))
                    col_dyn += 1

            row += 1

        for col, width in col_widths.items():
            sheet.set_column(col, col, width + 3)

        workbook.close()
        return output.getvalue()


class PayrollOrganikReportWizard(models.TransientModel):
    _name = 'payroll.organik.report.wizard'
    _description = 'Report Payroll Organik'

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: date.today()
    )
    all_branch = fields.Boolean(
        string='All Branches',
        default=False,
        help="Jika dicentang, maka semua cabang akan dipilih."
    )
    hr_branch_ids = fields.Many2many(
        'hr.branch',
        string='Cabang',
        help="Pilih satu atau beberapa cabang. Abaikan jika 'All Branches' dicentang."
    )

    def action_print_excel(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]

        if not self.all_branch and self.hr_branch_ids:
            domain.append(('employee_id.hr_branch_id', 'in', self.hr_branch_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)

        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type
                         and slip.employee_id.employment_type == 'organik'
                         and not slip.contract_id.grade_id.grade_type
        )

        if not payslips:
            raise UserError("Tidak ada payslip yang ditemukan dengan kriteria tersebut.")

        # --- Pengumpulan Data Dinamis dengan Urutan berdasarkan Sequence ---
        # Struktur awal: { cat_name: { rule_name: sequence } }
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                seq = line.sequence or 0
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], seq)
                else:
                    category_lines_map[cat_name][rule_name] = seq

        # Simpan nilai minimum sequence per kategori sebelum mengubah ke list
        category_sequence = {}
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda item: item[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            # Ubah dictionary rule menjadi list (yang terurut berdasarkan sequence)
            category_lines_map[cat] = [rule for rule, seq in sorted_rules]

        # Urutkan kategori berdasarkan nilai minimum sequence yang tersimpan
        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        # --- Pengelompokan Payslips Berdasarkan Cabang ---
        grouped_payslips = {}
        for slip in payslips:
            branch = slip.employee_id.hr_branch_id or False
            grouped_payslips.setdefault(branch, []).append(slip)

        branch_data_map = {}
        branch_totals_map = {}

        for branch, slip_list in grouped_payslips.items():
            branch_totals_map[branch] = {}
            for cat in sorted_categories:
                branch_totals_map[branch][cat] = {}
                for rule_name in category_lines_map[cat]:
                    branch_totals_map[branch][cat][rule_name] = 0.0

            data_for_branch = []
            counter = 1
            for slip in slip_list:
                row_data = {
                    'no': counter,
                    'nama': slip.employee_id.name or '',
                    'nip': slip.employee_id.nip_organik or '',
                    'jabatan': slip.employee_id.keterangan_jabatan_id.name or '',
                    'lines_by_cat': {},
                }
                for cat in sorted_categories:
                    row_data['lines_by_cat'][cat] = {}
                    for rule_name in category_lines_map[cat]:
                        row_data['lines_by_cat'][cat][rule_name] = 0.0
                for line in slip.line_ids:
                    cat_name = line.category_id.name if line.category_id else "Undefined"
                    rule_name = line.name or "No Name"
                    if cat_name in row_data['lines_by_cat'] and rule_name in row_data['lines_by_cat'][cat_name]:
                        row_data['lines_by_cat'][cat_name][rule_name] += line.total
                        branch_totals_map[branch][cat_name][rule_name] += line.total
                data_for_branch.append(row_data)
                counter += 1

            branch_data_map[branch] = data_for_branch

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        file_data = self._generate_excel_file(
            branch_data_map,
            branch_totals_map,
            category_lines_map,
            sorted_categories,
            month_name,
            year_str
        )

        attachment = self.env['ir.attachment'].create({
            'name': f'Daftar_Gaji_{month_name}_{year_str}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }

    def _generate_excel_file(self, branch_data_map, branch_totals_map,
                             category_lines_map, sorted_categories,
                             month_name, year_str):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Daftar Gaji")

        # === Format Cells ===
        top_title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4472C4',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })

        sheet.merge_range(0, 0, 0, 10, "DAFTAR GAJI PEGAWAI PERUSAHAAN", top_title_format)
        sheet.merge_range(1, 0, 1, 10, f"BULAN {month_name} {year_str}", top_title_format)

        current_row = 3
        col_widths = {}

        static_headers = ["No", "Nama", "NIP", "Jabatan"]

        total_dynamic_cols = sum(len(category_lines_map[cat]) for cat in sorted_categories)
        total_static_cols = len(static_headers)
        last_col_index = total_static_cols + total_dynamic_cols - 1

        def update_col_width(col, val):
            current_len = col_widths.get(col, 0)
            col_widths[col] = max(current_len, len(str(val)))

        # Loop per-cabang
        for branch, data_for_branch in branch_data_map.items():
            branch_name = branch.name if branch else "Tanpa Cabang"
            sheet.merge_range(current_row, 0, current_row, last_col_index,
                              f"Cabang: {branch_name}",
                              top_title_format)
            current_row += 1

            row_cat = current_row
            row_rule = current_row + 1

            for col, hdr in enumerate(static_headers):
                sheet.merge_range(row_cat, col, row_rule, col, hdr, header_format)
                update_col_width(col, hdr)

            col_offset = len(static_headers)
            for cat in sorted_categories:
                rules = category_lines_map[cat]
                num_rules = len(rules)
                if num_rules == 1:
                    sheet.write(row_cat, col_offset, cat, header_format)
                    sheet.write(row_rule, col_offset, rules[0], header_format)
                    update_col_width(col_offset, cat)
                    update_col_width(col_offset, rules[0])
                    col_offset += 1
                else:
                    sheet.merge_range(row_cat, col_offset,
                                      row_cat, col_offset + num_rules - 1,
                                      cat, header_format)
                    for idx, rule_name in enumerate(rules):
                        sheet.write(row_rule, col_offset + idx, rule_name, header_format)
                        update_col_width(col_offset + idx, rule_name)
                    col_offset += num_rules

            current_row += 2

            for row_data in data_for_branch:
                sheet.write(current_row, 0, row_data['no'], text_format)
                update_col_width(0, row_data['no'])

                sheet.write(current_row, 1, row_data['nama'], text_format)
                update_col_width(1, row_data['nama'])

                sheet.write(current_row, 2, row_data['nip'], text_format)
                update_col_width(2, row_data['nip'])

                sheet.write(current_row, 3, row_data['jabatan'], text_format)
                update_col_width(3, row_data['jabatan'])

                col_dyn = len(static_headers)
                for cat in sorted_categories:
                    for rule_name in category_lines_map[cat]:
                        amount = row_data['lines_by_cat'][cat][rule_name]
                        sheet.write_number(current_row, col_dyn, amount, currency_format)
                        amount_str = f"{int(amount):,}" if amount else "0"
                        update_col_width(col_dyn, amount_str)
                        col_dyn += 1

                current_row += 1

            # Baris total per-cabang
            sheet.write(current_row, 0, "TOTAL", header_format)
            for empty_col in [1, 2, 3]:
                sheet.write(current_row, empty_col, "", header_format)

            col_dyn = len(static_headers)
            for cat in sorted_categories:
                for rule_name in category_lines_map[cat]:
                    amount = branch_totals_map[branch][cat][rule_name]
                    sheet.write_number(current_row, col_dyn, amount, currency_format)
                    amount_str = f"{int(amount):,}" if amount else "0"
                    update_col_width(col_dyn, amount_str)
                    col_dyn += 1

            current_row += 2

        for col, w in col_widths.items():
            sheet.set_column(col, col, w + 3)

        workbook.close()
        return output.getvalue()

    def action_print_pdf(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if not self.all_branch and self.hr_branch_ids:
            domain.append(('employee_id.hr_branch_id', 'in', self.hr_branch_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type == 'organik' and not slip.contract_id.grade_id.grade_type
        )

        if not payslips:
            raise UserError("Tidak ada payslip yang ditemukan dengan kriteria tersebut.")

        # --- Pengumpulan Data Dinamis (menggunakan sequence) ---
        # Sebelumnya, data dikumpulkan sebagai set; sekarang kita simpan dalam dictionary dengan nilai sequence.
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                seq = line.sequence or 0  # Ambil nilai sequence (default 0 jika kosong)
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    # Simpan nilai sequence terkecil jika rule muncul lebih dari sekali
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], seq)
                else:
                    category_lines_map[cat_name][rule_name] = seq

        # Simpan nilai minimum sequence tiap kategori, lalu ubah tiap kategori menjadi list yang sudah terurut
        category_sequence = {}
        for cat_name in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat_name].items(), key=lambda item: item[1])
            category_sequence[cat_name] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat_name] = [rule for rule, seq in sorted_rules]

        # Urutkan kategori berdasarkan nilai minimum sequence tiap kategori
        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        # --- Pengolahan data untuk laporan PDF (kelompok per branch) ---
        branch_totals_map = {}
        for slip in payslips:
            branch = slip.employee_id.hr_branch_id or False
            if branch not in branch_totals_map:
                branch_totals_map[branch] = {
                    cat: {rule: 0.0 for rule in category_lines_map[cat]}
                    for cat in sorted_categories
                }
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                if cat_name in branch_totals_map[branch]:
                    if rule_name in branch_totals_map[branch][cat_name]:
                        branch_totals_map[branch][cat_name][rule_name] += line.total

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        report_data = {
            'branch_totals_map': branch_totals_map,
            'category_lines_map': category_lines_map,
            'sorted_categories': sorted_categories,
            'month_name': month_name,
            'year_str': year_str,
        }

        pdf = self.env.ref('payroll_ib.report_payroll_summary_pdf_template')._render_qweb_pdf(
            res_ids=self.ids,
            data={'data': report_data},
            report_ref='payroll_ib.report_payroll_summary_pdf_template_new_custom'
        )[0]

        attachment = self.env['ir.attachment'].create({
            'name': f'Rekap_Gaji_{month_name}_{year_str}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }


class PayrollPkwtReportWizard(models.TransientModel):
    _name = 'payroll.pkwt.report.wizard'
    _description = 'Report Payroll PKWT'

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: date.today()
    )
    all_branch = fields.Boolean(
        string='All Branches',
        default=False,
        help="Jika dicentang, maka semua cabang akan dipilih."
    )
    hr_branch_ids = fields.Many2many(
        'hr.branch',
        string='Cabang',
        help="Pilih satu atau beberapa cabang. Abaikan jika 'All Branches' dicentang."
    )

    def action_print_excel(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]

        if not self.all_branch and self.hr_branch_ids:
            domain.append(('employee_id.hr_branch_id', 'in', self.hr_branch_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type == 'pkwt'
        )

        if not payslips:
            raise UserError("Tidak ada payslip yang ditemukan dengan kriteria tersebut.")

        # --- Urut berdasarkan sequence ---
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat = line.category_id.name if line.category_id else "Undefined"
                rule = line.name or "No Name"
                seq = line.sequence or 0
                if cat not in category_lines_map:
                    category_lines_map[cat] = {}
                if rule in category_lines_map[cat]:
                    category_lines_map[cat][rule] = min(category_lines_map[cat][rule], seq)
                else:
                    category_lines_map[cat][rule] = seq

        category_sequence = {}
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda item: item[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat] = [rule for rule, _ in sorted_rules]

        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        grouped_payslips = {}
        for slip in payslips:
            branch = slip.employee_id.hr_branch_id or False
            grouped_payslips.setdefault(branch, []).append(slip)

        branch_data_map = {}
        branch_totals_map = {}

        for branch, slip_list in grouped_payslips.items():
            branch_totals_map[branch] = {
                cat: {rule: 0.0 for rule in category_lines_map[cat]}
                for cat in sorted_categories
            }

            data_for_branch = []
            for idx, slip in enumerate(slip_list, 1):
                row_data = {
                    'no': idx,
                    'nama': slip.employee_id.name or '',
                    'key': slip.employee_id.nip_pkwt or '',
                    'jabatan': slip.employee_id.keterangan_jabatan_id.name or '',
                    'lines_by_cat': {
                        cat: {rule: 0.0 for rule in category_lines_map[cat]}
                        for cat in sorted_categories
                    },
                }

                for line in slip.line_ids:
                    cat = line.category_id.name if line.category_id else "Undefined"
                    rule = line.name or "No Name"
                    if cat in row_data['lines_by_cat'] and rule in row_data['lines_by_cat'][cat]:
                        row_data['lines_by_cat'][cat][rule] += line.total
                        branch_totals_map[branch][cat][rule] += line.total

                data_for_branch.append(row_data)

            branch_data_map[branch] = data_for_branch

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        file_data = self._generate_excel_file(
            branch_data_map,
            branch_totals_map,
            category_lines_map,
            sorted_categories,
            month_name,
            year_str
        )

        attachment = self.env['ir.attachment'].create({
            'name': f'Daftar_Gaji_{month_name}_{year_str}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }

    def _generate_excel_file(self, branch_data_map, branch_totals_map,
                             category_lines_map, sorted_categories,
                             month_name, year_str):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Daftar Gaji")

        # === Format Cells ===
        top_title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4472C4',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })

        sheet.merge_range(0, 0, 0, 10, "DAFTAR GAJI / HONORARIUM KARYAWAN PKWT", top_title_format)
        sheet.merge_range(1, 0, 1, 10, f"BULAN {month_name} {year_str}", top_title_format)

        current_row = 3
        col_widths = {}

        static_headers = ["No", "Nama", "Key", "Jabatan"]

        total_dynamic_cols = sum(len(category_lines_map[cat]) for cat in sorted_categories)
        total_static_cols = len(static_headers)
        last_col_index = total_static_cols + total_dynamic_cols - 1

        def update_col_width(col, val):
            current_len = col_widths.get(col, 0)
            col_widths[col] = max(current_len, len(str(val)))

        # Loop per-cabang
        for branch, data_for_branch in branch_data_map.items():
            branch_name = branch.name if branch else "Tanpa Cabang"

            sheet.merge_range(current_row, 0, current_row, last_col_index,
                              f"Cabang: {branch_name}",
                              top_title_format)
            current_row += 1

            row_cat = current_row
            row_rule = current_row + 1

            for col, hdr in enumerate(static_headers):
                sheet.merge_range(row_cat, col, row_rule, col, hdr, header_format)
                update_col_width(col, hdr)

            col_offset = len(static_headers)
            for cat in sorted_categories:
                rules = category_lines_map[cat]
                num_rules = len(rules)
                if num_rules == 1:
                    sheet.write(row_cat, col_offset, cat, header_format)
                    sheet.write(row_rule, col_offset, rules[0], header_format)
                    update_col_width(col_offset, cat)
                    update_col_width(col_offset, rules[0])
                    col_offset += 1
                else:
                    sheet.merge_range(row_cat, col_offset,
                                      row_cat, col_offset + num_rules - 1,
                                      cat, header_format)
                    for idx, rule_name in enumerate(rules):
                        sheet.write(row_rule, col_offset + idx, rule_name, header_format)
                        update_col_width(col_offset + idx, cat)
                        update_col_width(col_offset + idx, rule_name)
                    col_offset += num_rules

            current_row += 2

            for row_data in data_for_branch:
                sheet.write(current_row, 0, row_data['no'], text_format)
                update_col_width(0, row_data['no'])

                sheet.write(current_row, 1, row_data['nama'], text_format)
                update_col_width(1, row_data['nama'])

                sheet.write(current_row, 2, row_data['key'], text_format)
                update_col_width(2, row_data['key'])

                sheet.write(current_row, 3, row_data['jabatan'], text_format)
                update_col_width(3, row_data['jabatan'])

                col_dyn = len(static_headers)
                for cat in sorted_categories:
                    for rule_name in category_lines_map[cat]:
                        amount = row_data['lines_by_cat'][cat][rule_name]
                        sheet.write_number(current_row, col_dyn, amount, currency_format)
                        amount_str = f"{int(amount):,}" if amount else "0"
                        update_col_width(col_dyn, amount_str)
                        col_dyn += 1

                current_row += 1

            # Baris total per-cabang
            sheet.write(current_row, 0, "TOTAL", header_format)
            for empty_col in [1, 2, 3]:
                sheet.write(current_row, empty_col, "", header_format)

            col_dyn = len(static_headers)
            for cat in sorted_categories:
                for rule_name in category_lines_map[cat]:
                    amount = branch_totals_map[branch][cat][rule_name]
                    sheet.write_number(current_row, col_dyn, amount, currency_format)
                    amount_str = f"{int(amount):,}" if amount else "0"
                    update_col_width(col_dyn, amount_str)
                    col_dyn += 1

            current_row += 2

        for col, w in col_widths.items():
            sheet.set_column(col, col, w + 3)

        workbook.close()
        return output.getvalue()

    def action_print_pdf(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if not self.all_branch and self.hr_branch_ids:
            domain.append(('employee_id.hr_branch_id', 'in', self.hr_branch_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type == 'pkwt'
        )

        if not payslips:
            raise UserError("Tidak ada payslip yang ditemukan dengan kriteria tersebut.")

        # --- Susun urutan rule berdasarkan sequence ---
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                seq = line.sequence or 0
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], seq)
                else:
                    category_lines_map[cat_name][rule_name] = seq

        category_sequence = {}
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda item: item[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat] = [rule for rule, seq in sorted_rules]

        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        # --- Hitung Total per Cabang per Rule ---
        branch_totals_map = {}
        for slip in payslips:
            branch = slip.employee_id.hr_branch_id or False
            if branch not in branch_totals_map:
                branch_totals_map[branch] = {
                    cat: {rule: 0.0 for rule in category_lines_map[cat]}
                    for cat in sorted_categories
                }
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                if cat_name in branch_totals_map[branch] and rule_name in branch_totals_map[branch][cat_name]:
                    branch_totals_map[branch][cat_name][rule_name] += line.total

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        report_data = {
            'branch_totals_map': branch_totals_map,
            'category_lines_map': category_lines_map,
            'sorted_categories': sorted_categories,
            'month_name': month_name,
            'year_str': year_str,
        }

        pdf = self.env.ref('payroll_ib.report_payroll_pkwt_summary_pdf_template')._render_qweb_pdf(
            res_ids=self.ids,
            data={'data': report_data},
            report_ref='payroll_ib.report_payroll_pkwt_summary_pdf_template_new'
        )[0]

        attachment = self.env['ir.attachment'].create({
            'name': f'Rekap_Gaji_{month_name}_{year_str}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }


class PayrollDireksiReportWizard(models.TransientModel):
    _name = 'payroll.direksi.report.wizard'
    _description = 'Report Payroll Direksi'

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: date.today()
    )
    all_branch = fields.Boolean(
        string='All Branches',
        default=False,
        help="Jika dicentang, maka semua cabang akan dipilih."
    )
    hr_branch_ids = fields.Many2many(
        'hr.branch',
        string='Cabang',
        help="Pilih satu atau beberapa cabang. Abaikan jika 'All Branches' dicentang."
    )

    def action_print_excel(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if not self.all_branch and self.hr_branch_ids:
            domain.append(('employee_id.hr_branch_id', 'in', self.hr_branch_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type in ['organik', 'pkwt']
                         and slip.employee_id.direksi
                         and slip.employee_id.grade_id.grade_type in ['direktur_utama', 'direktur']
        )

        if not payslips:
            raise UserError("Tidak ada payslip Direksi yang ditemukan dengan kriteria tersebut.")

        # --- Urutan berdasarkan sequence
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat = line.category_id.name if line.category_id else 'Undefined'
                rule = line.name or 'No Name'
                seq = line.sequence or 0
                if cat not in category_lines_map:
                    category_lines_map[cat] = {}
                if rule in category_lines_map[cat]:
                    category_lines_map[cat][rule] = min(seq, category_lines_map[cat][rule])
                else:
                    category_lines_map[cat][rule] = seq

        category_sequence = {}
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda x: x[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat] = [rule for rule, _ in sorted_rules]

        sorted_categories = sorted(category_lines_map, key=lambda x: category_sequence[x])

        # --- Grouping
        grouped_payslips = {}
        for slip in payslips:
            branch = slip.employee_id.hr_branch_id or False
            grouped_payslips.setdefault(branch, []).append(slip)

        branch_data_map = {}
        branch_totals_map = {}

        for branch, slip_list in grouped_payslips.items():
            branch_totals_map[branch] = {
                cat: {rule: 0.0 for rule in category_lines_map[cat]}
                for cat in sorted_categories
            }

            data_for_branch = []
            for i, slip in enumerate(slip_list, start=1):
                row = {
                    'no': i,
                    'nama': slip.employee_id.name or '',
                    'jabatan': slip.employee_id.keterangan_jabatan_id.name or '',
                    'lines_by_cat': {
                        cat: {rule: 0.0 for rule in category_lines_map[cat]}
                        for cat in sorted_categories
                    }
                }
                for line in slip.line_ids:
                    cat = line.category_id.name if line.category_id else 'Undefined'
                    rule = line.name or 'No Name'
                    if cat in row['lines_by_cat'] and rule in row['lines_by_cat'][cat]:
                        row['lines_by_cat'][cat][rule] += line.total
                        branch_totals_map[branch][cat][rule] += line.total
                data_for_branch.append(row)
            branch_data_map[branch] = data_for_branch

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        file_data = self._generate_excel_file(
            branch_data_map,
            branch_totals_map,
            category_lines_map,
            sorted_categories,
            month_name,
            year_str
        )

        attachment = self.env['ir.attachment'].create({
            'name': f'Daftar_Gaji_Direksi_{month_name}_{year_str}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }

    def _generate_excel_file(self, branch_data_map, branch_totals_map,
                             category_lines_map, sorted_categories,
                             month_name, year_str):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Daftar Gaji")

        # === Format Cells ===
        top_title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4472C4',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })

        sheet.merge_range(0, 0, 0, 10, "DAFTAR GAJI / HONORARIUM DIREKSI", top_title_format)
        sheet.merge_range(1, 0, 1, 10, f"BULAN {month_name} {year_str}", top_title_format)

        current_row = 3
        col_widths = {}

        static_headers = ["No", "Nama", "Jabatan"]

        total_dynamic_cols = sum(len(category_lines_map[cat]) for cat in sorted_categories)
        total_static_cols = len(static_headers)
        last_col_index = total_static_cols + total_dynamic_cols - 1

        def update_col_width(col, val):
            current_len = col_widths.get(col, 0)
            col_widths[col] = max(current_len, len(str(val)))

        # Loop per-cabang
        for branch, data_for_branch in branch_data_map.items():
            branch_name = branch.name if branch else ""

            sheet.merge_range(current_row, 0, current_row, last_col_index,
                              f"{branch_name}",
                              top_title_format)
            current_row += 1

            row_cat = current_row
            row_rule = current_row + 1

            for col, hdr in enumerate(static_headers):
                sheet.merge_range(row_cat, col, row_rule, col, hdr, header_format)
                update_col_width(col, hdr)

            col_offset = len(static_headers)
            for cat in sorted_categories:
                rules = category_lines_map[cat]
                num_rules = len(rules)
                if num_rules == 1:
                    sheet.write(row_cat, col_offset, cat, header_format)
                    sheet.write(row_rule, col_offset, rules[0], header_format)
                    update_col_width(col_offset, cat)
                    update_col_width(col_offset, rules[0])
                    col_offset += 1
                else:
                    sheet.merge_range(row_cat, col_offset,
                                      row_cat, col_offset + num_rules - 1,
                                      cat, header_format)
                    for idx, rule_name in enumerate(rules):
                        sheet.write(row_rule, col_offset + idx, rule_name, header_format)
                        update_col_width(col_offset + idx, cat)
                        update_col_width(col_offset + idx, rule_name)
                    col_offset += num_rules

            current_row += 2

            for row_data in data_for_branch:
                sheet.write(current_row, 0, row_data['no'], text_format)
                update_col_width(0, row_data['no'])

                sheet.write(current_row, 1, row_data['nama'], text_format)
                update_col_width(1, row_data['nama'])

                sheet.write(current_row, 3, row_data['jabatan'], text_format)
                update_col_width(3, row_data['jabatan'])

                col_dyn = len(static_headers)
                for cat in sorted_categories:
                    for rule_name in category_lines_map[cat]:
                        amount = row_data['lines_by_cat'][cat][rule_name]
                        sheet.write_number(current_row, col_dyn, amount, currency_format)
                        amount_str = f"{int(amount):,}" if amount else "0"
                        update_col_width(col_dyn, amount_str)
                        col_dyn += 1

                current_row += 1

            # Baris total per-cabang
            sheet.write(current_row, 0, "TOTAL", header_format)
            for empty_col in [1, 2, 3]:
                sheet.write(current_row, empty_col, "", header_format)

            col_dyn = len(static_headers)
            for cat in sorted_categories:
                for rule_name in category_lines_map[cat]:
                    amount = branch_totals_map[branch][cat][rule_name]
                    sheet.write_number(current_row, col_dyn, amount, currency_format)
                    amount_str = f"{int(amount):,}" if amount else "0"
                    update_col_width(col_dyn, amount_str)
                    col_dyn += 1

            current_row += 2

        for col, w in col_widths.items():
            sheet.set_column(col, col, w + 3)

        workbook.close()
        return output.getvalue()

    def action_print_pdf(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if not self.all_branch and self.hr_branch_ids:
            domain.append(('employee_id.hr_branch_id', 'in', self.hr_branch_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: (
                    slip.employee_id.employment_type in ['organik', 'pkwt']
                    and slip.employee_id.direksi
                    and slip.employee_id.grade_id.grade_type in ['direktur_utama', 'direktur']
            )
        )

        if not payslips:
            raise UserError("Tidak ada payslip Direksi yang ditemukan dengan kriteria tersebut.")

        # === Kumpulkan kolom dinamis berdasarkan SEQUENCE ===
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                seq = line.sequence or 0
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], seq)
                else:
                    category_lines_map[cat_name][rule_name] = seq

        category_sequence = {}
        for cat_name in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat_name].items(), key=lambda x: x[1])
            category_sequence[cat_name] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat_name] = [rule for rule, _ in sorted_rules]

        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        # === Hitung total per rule ===
        direksi_totals_map = {
            cat: {rule: 0.0 for rule in category_lines_map[cat]}
            for cat in sorted_categories
        }

        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                if cat_name in direksi_totals_map and rule_name in direksi_totals_map[cat_name]:
                    direksi_totals_map[cat_name][rule_name] += line.total

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        report_data = {
            'sorted_categories': sorted_categories,
            'category_lines_map': category_lines_map,
            'direksi_totals_map': direksi_totals_map,
            'month_name': month_name,
            'year_str': year_str,
        }

        pdf = self.env.ref('payroll_ib.report_payroll_direksi_pdf_template')._render_qweb_pdf(
            res_ids=self.ids,
            data={'data': report_data},
            report_ref='payroll_ib.report_payroll_direksi_pdf_template_new'
        )[0]

        attachment = self.env['ir.attachment'].create({
            'name': f'Rekap_Gaji_Direksi_{month_name}_{year_str}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }


class PayrollDekomReportWizard(models.TransientModel):
    _name = 'payroll.dekom.report.wizard'
    _description = 'Report Payroll Dekom'

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=lambda self: date.today()
    )
    all_jabatan = fields.Boolean(
        string='All Jabatans',
        default=False,
        help="Jika dicentang, maka semua jabatan akan dipilih."
    )
    jabatan_komplit_ids = fields.Many2many(
        'hr.employee.jabatan.komplit',
        string='Jabatan',
        help="Pilih satu atau beberapa jabatan. Abaikan jika 'All Jabatans' dicentang."
    )

    def action_print_excel(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]

        if not self.all_jabatan and self.jabatan_komplit_ids:
            domain.append(('employee_id.jabatan_komplit_id', 'in', self.jabatan_komplit_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type in ['organik', 'pkwt']
                         and slip.employee_id.grade_id.grade_type not in ['direktur_utama', 'direktur']
        )

        if not payslips:
            raise UserError("Tidak ada payslip yang ditemukan dengan kriteria tersebut.")

        # KUMPULKAN RULE BERDASARKAN SEQUENCE
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                seq = line.sequence or 0
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], seq)
                else:
                    category_lines_map[cat_name][rule_name] = seq

        # Urutkan rule dalam kategori, dan urutkan kategori berdasarkan sequence terkecil
        category_sequence = {}
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda item: item[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat] = [rule for rule, _ in sorted_rules]

        sorted_categories = sorted(category_sequence.keys(), key=lambda cat: category_sequence[cat])

        # PENGELOMPOKAN DATA PER JABATAN KOMPLIT
        grouped_payslips = {}
        for slip in payslips:
            jabatan_komplit = slip.employee_id.jabatan_komplit_id or False
            grouped_payslips.setdefault(jabatan_komplit, []).append(slip)

        jabatan_data_map = {}
        jabatan_totals_map = {}

        for jabatan_komplit, slip_list in grouped_payslips.items():
            jabatan_totals_map[jabatan_komplit] = {
                cat: {rule: 0.0 for rule in category_lines_map[cat]}
                for cat in sorted_categories
            }

            data_for_jabatan = []
            counter = 1
            for slip in slip_list:
                row_data = {
                    'no': counter,
                    'nama': slip.employee_id.name or '',
                    'jabatan': slip.employee_id.jabatan_komplit_id.name or '',
                    'lines_by_cat': {
                        cat: {rule: 0.0 for rule in category_lines_map[cat]}
                        for cat in sorted_categories
                    }
                }

                for line in slip.line_ids:
                    cat_name = line.category_id.name if line.category_id else "Undefined"
                    rule_name = line.name or "No Name"
                    if cat_name in row_data['lines_by_cat'] and rule_name in row_data['lines_by_cat'][cat_name]:
                        row_data['lines_by_cat'][cat_name][rule_name] += line.total
                        jabatan_totals_map[jabatan_komplit][cat_name][rule_name] += line.total

                data_for_jabatan.append(row_data)
                counter += 1

            jabatan_data_map[jabatan_komplit] = data_for_jabatan

        # GENERATE FILE
        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        file_data = self._generate_excel_file(
            jabatan_data_map,
            jabatan_totals_map,
            category_lines_map,
            sorted_categories,
            month_name,
            year_str
        )

        attachment = self.env['ir.attachment'].create({
            'name': f'Daftar_Gaji_{month_name}_{year_str}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }

    def _generate_excel_file(self, jabatan_data_map, jabatan_totals_map,
                             category_lines_map, sorted_categories,
                             month_name, year_str):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Daftar Gaji")

        # === Format Cells ===
        top_title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 14,
        })
        header_format = workbook.add_format({
            'bold': True,
            'font_color': 'white',
            'bg_color': '#4472C4',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        currency_format = workbook.add_format({
            'num_format': '#,##0',
            'border': 1,
            'align': 'right',
            'valign': 'vcenter'
        })

        # === Header Utama di Paling Atas ===
        sheet.merge_range(0, 0, 0, 10,
                          "DAFTAR HONORARIUM DEWAN KOMISARIS, SEKRETARIS DEKOM dan ANGGOTA KOMITE",
                          top_title_format)
        sheet.merge_range(1, 0, 1, 10,
                          f"BULAN {month_name} {year_str}",
                          top_title_format)

        current_row = 3
        col_widths = {}

        static_headers = ["No", "Nama", "Jabatan"]

        total_dynamic_cols = sum(len(category_lines_map[cat]) for cat in sorted_categories)
        total_static_cols = len(static_headers)
        last_col_index = total_static_cols + total_dynamic_cols - 1

        def update_col_width(col, val):
            current_len = col_widths.get(col, 0)
            col_widths[col] = max(current_len, len(str(val)))

        for jabatan_komplit, data_for_jabatan in jabatan_data_map.items():
            jabatan_name = jabatan_komplit.name if jabatan_komplit else ""
            sheet.merge_range(current_row, 0, current_row, last_col_index,
                              jabatan_name,
                              top_title_format)
            current_row += 1

            row_cat = current_row
            row_rule = current_row + 1

            for col, hdr in enumerate(static_headers):
                sheet.merge_range(row_cat, col, row_rule, col, hdr, header_format)
                update_col_width(col, hdr)

            col_offset = len(static_headers)
            for cat in sorted_categories:
                rules = category_lines_map[cat]
                num_rules = len(rules)
                if num_rules == 1:
                    sheet.write(row_cat, col_offset, cat, header_format)
                    sheet.write(row_rule, col_offset, rules[0], header_format)
                    update_col_width(col_offset, cat)
                    update_col_width(col_offset, rules[0])
                    col_offset += 1
                else:
                    sheet.merge_range(row_cat, col_offset,
                                      row_cat, col_offset + num_rules - 1,
                                      cat, header_format)
                    for idx, rule_name in enumerate(rules):
                        sheet.write(row_rule, col_offset + idx, rule_name, header_format)
                        update_col_width(col_offset + idx, cat)
                        update_col_width(col_offset + idx, rule_name)
                    col_offset += num_rules

            current_row += 2

            for row_data in data_for_jabatan:
                sheet.write(current_row, 0, row_data['no'], text_format)
                update_col_width(0, row_data['no'])

                sheet.write(current_row, 1, row_data['nama'], text_format)
                update_col_width(1, row_data['nama'])

                sheet.write(current_row, 2, row_data['jabatan'], text_format)
                update_col_width(2, row_data['jabatan'])

                col_dyn = len(static_headers)
                for cat in sorted_categories:
                    for rule_name in category_lines_map[cat]:
                        amount = row_data['lines_by_cat'][cat][rule_name]
                        sheet.write_number(current_row, col_dyn, amount, currency_format)
                        amount_str = f"{int(amount):,}" if amount else "0"
                        update_col_width(col_dyn, amount_str)
                        col_dyn += 1

                current_row += 1

            sheet.write(current_row, 0, "TOTAL", header_format)
            for empty_col in [1, 2]:
                sheet.write(current_row, empty_col, "", header_format)

            col_dyn = len(static_headers)
            for cat in sorted_categories:
                for rule_name in category_lines_map[cat]:
                    amount = jabatan_totals_map[jabatan_komplit][cat][rule_name]
                    sheet.write_number(current_row, col_dyn, amount, currency_format)
                    amount_str = f"{int(amount):,}" if amount else "0"
                    update_col_width(col_dyn, amount_str)
                    col_dyn += 1

            current_row += 2

        for col, w in col_widths.items():
            sheet.set_column(col, col, w + 3)

        workbook.close()
        return output.getvalue()

    def action_print_pdf(self):
        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if not self.all_jabatan and self.jabatan_komplit_ids:
            domain.append(('employee_id.jabatan_komplit_id', 'in', self.jabatan_komplit_ids.ids))

        payslips = self.env['hr.payslip'].search(domain)
        payslips = payslips.filtered(
            lambda slip: slip.employee_id.employment_type in ['organik', 'pkwt']
                         and slip.employee_id.grade_id.grade_type not in ['direktur_utama', 'direktur']
        )

        if not payslips:
            raise UserError("Tidak ada payslip yang ditemukan dengan kriteria tersebut.")

        # --- Mapping berdasarkan SEQUENCE ---
        category_lines_map = {}
        for slip in payslips:
            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                sequence = line.sequence or 0
                if cat_name not in category_lines_map:
                    category_lines_map[cat_name] = {}
                if rule_name in category_lines_map[cat_name]:
                    category_lines_map[cat_name][rule_name] = min(category_lines_map[cat_name][rule_name], sequence)
                else:
                    category_lines_map[cat_name][rule_name] = sequence

        category_sequence = {}
        for cat in category_lines_map:
            sorted_rules = sorted(category_lines_map[cat].items(), key=lambda item: item[1])
            category_sequence[cat] = sorted_rules[0][1] if sorted_rules else 0
            category_lines_map[cat] = [rule for rule, _ in sorted_rules]

        sorted_categories = sorted(category_lines_map.keys(), key=lambda cat: category_sequence[cat])

        # --- Pengolahan Total Per Jabatan ---
        jabatan_totals_map = {}
        for slip in payslips:
            jab = slip.employee_id.jabatan_komplit_id or False
            if jab not in jabatan_totals_map:
                jabatan_totals_map[jab] = {
                    cat: {rule: 0.0 for rule in category_lines_map[cat]}
                    for cat in sorted_categories
                }

            for line in slip.line_ids:
                cat_name = line.category_id.name if line.category_id else "Undefined"
                rule_name = line.name or "No Name"
                if cat_name in jabatan_totals_map[jab] and rule_name in jabatan_totals_map[jab][cat_name]:
                    jabatan_totals_map[jab][cat_name][rule_name] += line.total

        sorted_jabatans = sorted(jabatan_totals_map.keys(), key=lambda j: j.name if j else "")

        month_name = calendar.month_name[self.date_to.month].upper()
        year_str = str(self.date_to.year)

        report_data = {
            'sorted_categories': sorted_categories,
            'category_lines_map': category_lines_map,
            'jabatan_totals_map': jabatan_totals_map,
            'sorted_jabatans': sorted_jabatans,
            'month_name': month_name,
            'year_str': year_str,
        }

        pdf = self.env.ref('payroll_ib.report_payroll_dekom_pdf_template')._render_qweb_pdf(
            res_ids=self.ids,
            data={'data': report_data},
            report_ref='payroll_ib.report_payroll_dekom_pdf_template_new'
        )[0]

        attachment = self.env['ir.attachment'].create({
            'name': f'Daftar_Gaji_DEKOM_{month_name}_{year_str}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf),
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{attachment.id}?download=false",
            'target': 'new',
        }