import io
import xlsxwriter
from odoo import models, fields, api
from odoo.tools import pycompat
import base64
from babel.dates import format_date


class SinkingFundExportWizard(models.TransientModel):
    _name = 'sinking.fund.export.wizard'
    _description = 'Wizard Export Sinking Fund'

    sinking_fund_ids = fields.Many2many(
            comodel_name='account.keuangan.sinking',
            string='Data Sinking Fund'
        )
    
    tipe_notes = fields.Selection([   
        ('mtn', 'MTN'),
        ('ltn', 'LTN'),
        ('ipk', 'Imbalan Pasca Kerja'),
        # Tambahkan status lain jika perlu
    ], tracking=True) 


    summary_sinking_fund = fields.Float(string='Summary Sinking Fund', compute='_compute_summary')
    summary_deposito= fields.Float(string='Summary Deposito', compute='_compute_summary')
    summary_pendapatan_biaya = fields.Float(string='Summary Pendapatan Biaya', compute='_compute_summary')
    summary_saldo = fields.Float(string='Summary Saldo', compute='_compute_summary')

    # branch_id = fields.Many2one('res.branch', string='Nama Cabang', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)

    user_branch_id = fields.Many2one(
        'res.branch', 
        string='User Branch', 
        compute='_compute_user_branch', 
        store=True
    )
    branch_address = fields.Char(
        string='Branch Address', 
        compute='_compute_user_branch', 
        store=True
    )

    phone_branch = fields.Char(compute="_compute_user_branch_phone", store=True)
    email_branch = fields.Char(compute="_compute_user_branch_email", store=True)
    website_branch = fields.Char(compute="_compute_user_branch_website", store=True)

    tipe_notes_display = fields.Char(string='Tipe Notes Label', compute='_compute_tipe_notes_display', store=False)

    @api.depends('tipe_notes')
    def _compute_tipe_notes_display(self):
        for wizard in self:
            wizard.tipe_notes_display = dict(self._fields['tipe_notes'].selection).get(wizard.tipe_notes, '')

    @api.depends('user_id.branch_id')
    def _compute_user_branch(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.user_branch_id = branch
            if branch:
                address = f"{branch.street or ''}, {branch.street2 or ''}, {branch.city or ''}, {branch.state_id.name or ''}, {branch.zip or ''}"
                record.branch_address = address.strip(', ')
            else:
                record.branch_address = ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_phone(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.phone_branch = branch.phone or ''

   
    @api.depends('user_id.branch_id')
    def _compute_user_branch_email(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.email_branch = branch.email or ''

    @api.depends('user_id.branch_id')
    def _compute_user_branch_website(self):
        for record in self:
            user = self.env.user
            branch = user.branch_id  # Mengambil branch dari user yang login
            record.website_branch = branch.website or ''
            

    @api.depends('tipe_notes')
    def _compute_summary(self):
        for wizard in self:
            domain = []
            if wizard.tipe_notes:
                domain.append(('tipe_notes', '=', wizard.tipe_notes))

            records = self.env['account.keuangan.sinking'].search(domain)
            wizard.summary_sinking_fund = sum(records.mapped('total_sinking_fund'))
            wizard.summary_deposito = sum(records.mapped('total_deposito'))
            wizard.summary_pendapatan_biaya = sum(records.mapped('total_biaya_admin'))
            wizard.summary_saldo = sum(records.mapped('total_saldo'))


    def action_preview(self):
        # Jika user memilih tipe_notes, filter berdasarkan itu
        if self.tipe_notes:
            domain = [('tipe_notes', '=', self.tipe_notes)]
        else:
            domain = []  # Tidak ada filter → ambil semua data

        records = self.env['account.keuangan.sinking'].search(domain)
        
        # Kirimkan records yang ditemukan ke laporan
        return self.env.ref('agp_keuangan_ib.action_report_sinking_fund_html').report_action(records)
            

    def action_export(self):
        # Jika tipe_bank_garansi_id dipilih, filter berdasarkan tipe tersebut
        if self.tipe_notes:
            domain = [('tipe_notes', '=', self.tipe_notes)]
        else:
            domain = []  # Tidak ada filter jika tipe_bank_garansi_id kosong

        records = self.env['account.keuangan.sinking'].search(domain)

        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Sinking Fund')

        # Set format judul (bold, center)
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vleft', 'font_size': 14})

        # Tulis judul di baris pertama (row 0), kolom A sampai O (15 kolom)
        judul = 'SINKING FUND'
        sheet.merge_range(0, 0, 0, 9, judul, title_format)

        headers = ['NO', 'NOMOR SINKING FUND', 'TIPE NOTES', 'BANK', 'REKENING', 'MATURITY DATE', 'TOTAL PENERIMAAN / PENGELUARAN SINKING FUND', 
                   'TOTAL PEMBUATAN / PENCAIRAN DEPOSITO', 'TOTAL PENDAPATAN DAN ADMINISTRASI BANK', 'SALDO', 'URAIAN NOTES']
        
        header_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#ff8c00', 'text_wrap': True})  # Optional: header abu-abu
        total_format = workbook.add_format({'align': 'right', 'valign': 'vright', 'bold': True, 'bg_color': '#158e1b'})  # Optional: header abu-abu

        column_widths = [len(h) for h in headers]

        # Tulis header
        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        # Inisialisasi total untuk kolom yang diinginkan
        summary_sinking_fund = 0
        summary_deposito = 0
        summary_pendapatan_biaya = 0
        summary_saldo = 0

        # Tulis data
        for row_num, record in enumerate(records, start=3):
            
            maturity_date = record.maturity_date.strftime('%d %b %Y').upper() if record.maturity_date else ''

            total_sinking_fund = float(record.total_sinking_fund) if record.total_sinking_fund else 0
            total_deposito = float(record.total_deposito) if record.total_deposito else 0
            total_biaya_admin = float(record.total_biaya_admin) if record.total_biaya_admin else 0
            total_saldo = float(record.total_saldo) if record.total_saldo else 0

            summary_sinking_fund += total_sinking_fund
            summary_deposito += total_deposito
            summary_pendapatan_biaya += total_biaya_admin
            summary_saldo += total_saldo

            row_data = [
                str(row_num - 2),
                record.name or '',
                record.tipe_notes_display or '',
                record.bank or '',
                record.rekening or '',
                maturity_date,
                "{:,.0f}".format(total_sinking_fund),
                "{:,.0f}".format(total_deposito),
                "{:,.0f}".format(total_biaya_admin),
                "{:,.0f}".format(total_saldo),
                record.uraian_notes or ''
            ]

            # Define format styles
            align_left_format = workbook.add_format({'align': 'left'})
            align_center_format = workbook.add_format({'align': 'center'})
            align_right_format = workbook.add_format({'align': 'right'})

            column_formats = [
                align_center_format,  # NO
                align_left_format,  # NOMOR SINKING FUND
                align_center_format,  # TIPE NOTES
                align_left_format,  # BANK
                align_left_format,  # REKENING
                align_center_format,  # MATURITY DATE
                align_right_format,  # TOTAL PENERIMAAN / PENGELUARAN SINKING FIND
                align_right_format,  # TOTAL PEMBUATAN / PENCAiRAN DEPOSITO
                align_right_format,  # TOTAL PENDAPATAN DAN ADMINISTRASI BANK
                align_right_format,  # SALDO
                align_left_format,  # URAIAN NOTES
            ]

            # Tulis ke Excel
            for col_num, cell_value in enumerate(row_data):
                sheet.write(row_num, col_num, cell_value, column_formats[col_num])

                # Update maksimal lebar kolom
                if isinstance(cell_value, str):
                    length = len(cell_value)
                else:
                    length = len(str(cell_value))

                if length > column_widths[col_num]:
                    column_widths[col_num] = length
            
        # Tambahkan baris total
        total_row = len(records) + 4  # Baris total berada setelah data terakhir

        # Menulis total di kolom yang sesuai
        for col_num in range(len(headers)):
            if col_num == 1:  
                sheet.write(total_row, 1, 'TOTAL', total_format)            
            elif col_num == 6:  
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_sinking_fund), total_format)  # Total nominal jaminan
            elif col_num == 7:  
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_deposito), total_format)  # Total biaya
            elif col_num == 8:  
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_pendapatan_biaya), total_format)  # Total dana kembali
            elif col_num == 9: 
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_saldo), total_format)  # Total dana kembali
            else:
                sheet.write(total_row, col_num, '', total_format)  # Kolom lainnya dikosongkan di baris total

        # Set lebar kolom berdasarkan data terpanjang
        for col_num, width in enumerate(column_widths):
            sheet.set_column(col_num, col_num, width + 2)  # Tambah margin supaya tidak mepet

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.getvalue()).decode('utf-8')  # Base64 encoding

        # Simpan ke ir.attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Sinking Fund.xlsx',  # Nama file yang diunduh
            'type': 'binary',
            'datas': file_data,  # Menyimpan file yang sudah di-encode dalam base64
            'store_fname': 'export_sinking_fund.xlsx',
            'res_model': 'account.keuangan.sinking',
            'res_id': self.id,
        })
        
        output.close()

        # Kembalikan URL untuk download attachment
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }


    def get_records_dict(self):
        domain = []
        if self.tipe_notes:
            domain.append(('tipe_notes', '=', self.tipe_notes))

        records = self.env['account.keuangan.sinking'].search(domain)

        result = []

        for idx, rec in enumerate(records, start=1):  # mulai dari 1

            result.append({
                'no': idx,
                'name': rec.name or '',
                'tipe_notes': rec.tipe_notes_display or '',
                'bank': rec.bank or '',
                'rekening': rec.rekening or '',
                'maturity_date': format_date(rec.maturity_date, format='d MMMM y', locale='id') if rec.maturity_date else '',
                'total_sinking_fund': "{:,.0f}".format(rec.total_sinking_fund or 0.0),
                'total_deposito': "{:,.0f}".format(rec.total_deposito or 0.0),
                'total_biaya_admin': "{:,.0f}".format(rec.total_biaya_admin or 0.0),
                'total_saldo': "{:,.0f}".format(rec.total_saldo or 0.0),
                'uraian_notes': rec.uraian_notes or '',
            })
        
        for res in result : 
           print("RECORDS =", records)
           print("RESULT =", res)
 
        return result
    
   
    def action_print_pdf(self):
        
        records = self.sinking_fund_ids

        record_dicts = self.get_records_dict()


        data = {
            'objects': record_dicts,
        }

        # print("RECORDS =", records)
        # print("DATA =", data)

        return self.env.ref('agp_report_py3o.sinking_fund_py3o').report_action(
            records,  # PENTING! harus record dari model bank garansi
            data={
            'objects': record_dicts,
        })   