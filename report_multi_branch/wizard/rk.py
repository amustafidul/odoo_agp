from odoo import models, fields, api
from odoo import models
import base64
import io
import xlsxwriter


class ReportRK(models.TransientModel):
    _name = 'rk.wizard'
    _description = 'R/K Report Wizard'

    branch_id = fields.Many2one('res.branch', string="Branch", required=False)
    account_id = fields.Many2one(
        'account.account',
        string="Account (R/K)",
        domain="[('name', 'ilike', 'R/K')]"
    )
    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    line_ids = fields.Many2many('account.move.line', string="Journal Items R/K", readonly=True)

    def _get_rk_move_lines(self):
        """
        Fungsi untuk mengambil baris jurnal dengan nama akun R/K.
        Dapat digunakan di berbagai tempat dalam model ini.
        """
        query = """
            SELECT aml.id
            FROM account_move_line aml
            JOIN account_account acc ON aml.account_id = acc.id
            WHERE acc.name ->> 'en_US' ILIKE %s
            AND (aml.display_type IS NULL OR aml.display_type NOT IN ('line_section', 'line_note'))
        """

        # Parameter pertama: cari akun dengan nama mengandung 'R/K'
        params = ['%R/K%']

        if self.account_id:
            query += " AND aml.account_id = %s"
            params.append(self.account_id.id)

        if self.date_from:
            query += " AND aml.date >= %s"
            params.append(self.date_from)

        if self.date_to:
            query += " AND aml.date <= %s"
            params.append(self.date_to)

        query += " ORDER BY aml.date DESC, aml.id DESC"

        # Eksekusi query dan ambil hasilnya
        self.env.cr.execute(query, params)
        line_ids = [r[0] for r in self.env.cr.fetchall()]
        return line_ids


    def get_rk_move_lines(self):
        # Panggil fungsi _get_rk_move_lines untuk mengambil baris jurnal
        line_ids = self._get_rk_move_lines()

        # Set line_ids ke field Many2many
        self.line_ids = [(6, 0, line_ids)]

        # Gunakan sudo() untuk mengembalikan record tanpa pembatasan akses
        return self.env['account.move.line'].sudo().browse(line_ids)

    def get_rk_lines_grouped_by_branch(self):
        grouped = {}
        move_lines = self.env['account.move.line'].sudo().browse(self._get_rk_move_lines())
        for line in move_lines:
            branch = line.move_id.branch_id.name or 'Tanpa Cabang'
            if branch not in grouped:
                grouped[branch] = []
            grouped[branch].append(line)
        return grouped.items()  # List of (branch_name, [lines])

    # def action_show_rk_lines(self):
    #     self.ensure_one()
        
    #     # Panggil fungsi _get_rk_move_lines untuk mengambil baris jurnal
    #     line_ids = self._get_rk_move_lines()
        
    #     # Set line_ids ke field Many2many
    #     self.line_ids = [(6, 0, line_ids)]

    #     # Return action untuk tetap berada di form view
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'rk.wizard',
    #         'view_mode': 'form',
    #         'res_id': self.id,
    #         'target': 'new',
    #         'context': {
    #             'search_default_filter_my_branch': 0,
    #             'allowed_branch_ids': False,  # Remove restrictions
    #         },
    #     }

    def action_view_rk_html(self):
        # Return report action
        return self.env.ref('report_multi_branch.report_rk').report_action(self)


    def action_export_rk_excel(self):
        self.ensure_one()
        lines = self._get_rk_move_lines()
        move_lines = self.env['account.move.line'].sudo().browse(lines)

        # Group by branch
        grouped_lines = {}
        for line in move_lines:
            branch_name = line.move_id.branch_id.name or 'Tanpa Cabang'
            grouped_lines.setdefault(branch_name, []).append(line)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Laporan R/K')

        # Formats
        header_format = workbook.add_format({'bold': True, 'bg_color': '#CCCCCC'})
        date_format = workbook.add_format({'num_format': 'dd-mm-yyyy'})
        text_format = workbook.add_format({'align': 'left'})
        bold_format = workbook.add_format({'bold': True})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'align': 'left'})
        subtotal_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'num_format': '#,##0.00'})

        # Filter info
        worksheet.write('A1', 'Date From', bold_format)
        worksheet.write('B1', str(self.date_from or '-'), text_format)

        worksheet.write('A2', 'Date To', bold_format)
        worksheet.write('B2', str(self.date_to or '-'), text_format)

        worksheet.write('A3', 'Account', bold_format)
        worksheet.write('B3', self.account_id.name or '', text_format)

        # Headers
        headers = [
            'Date', 'Journal', 'Branch', 'Number', 'Account', 'Partner', 'Reference',
            'No. Ref', 'Label', 'Note', 'Debit', 'Credit'
        ]
        column_widths = [15, 20, 15, 15, 20, 25, 20, 15, 30, 30, 15, 15]
        for i, width in enumerate(column_widths):
            worksheet.set_column(i, i, width)

        header_row = 5
        row = header_row

        for branch, lines in grouped_lines.items():
            # Title of branch group
            worksheet.write(row, 0, 'Branch:', bold_format)
            worksheet.write(row, 1, branch, bold_format)
            row += 1

            # Header row
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, header_format)
            row += 1

            total_debit = 0.0
            total_credit = 0.0

            worksheet.set_column(8, 8, 30, wrap_format)
            worksheet.set_column(9, 9, 30, wrap_format)  

            for line in lines:
                worksheet.write_datetime(row, 0, line.date or '', date_format)
                worksheet.write(row, 1, line.journal_id.name or '', text_format)
                worksheet.write(row, 2, line.move_id.branch_id.name or '', text_format)
                worksheet.write(row, 3, line.move_id.name or '', text_format)
                worksheet.write(row, 4, line.account_id.name or '', text_format)
                worksheet.write(row, 5, line.partner_id.name or '', text_format)
                worksheet.write(row, 6, line.move_id.ref or '', text_format)
                worksheet.write(row, 7, line.ref or '', text_format)
                worksheet.write(row, 8, line.name or '', wrap_format)
                worksheet.write(row, 9, line.move_id.narration or '', wrap_format) 
                worksheet.write_number(row, 10, line.debit or 0.0, number_format)
                worksheet.write_number(row, 11, line.credit or 0.0, number_format)

                total_debit += line.debit or 0.0
                total_credit += line.credit or 0.0
                row += 1

            # Subtotal per branch
            worksheet.write(row, 9, 'Subtotal', bold_format)
            worksheet.write_number(row, 10, total_debit, subtotal_format)
            worksheet.write_number(row, 11, total_credit, subtotal_format)
            row += 2  # Add empty line after each group

        workbook.close()
        output.seek(0)
        excel_data = output.read()

        # Create attachment and return as download
        attachment = self.env['ir.attachment'].create({
            'name': 'Laporan_RK.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
