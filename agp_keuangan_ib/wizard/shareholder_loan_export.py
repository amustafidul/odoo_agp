import io
import xlsxwriter
from odoo import models, fields, api
from odoo.tools import pycompat
import base64
from babel.dates import format_date


class ShlExportWizard(models.TransientModel):
    _name = 'shl.export.wizard'
    _description = 'Wizard Export Shareholder Loan'

    shl_ids = fields.Many2many(
            comodel_name='account.keuangan.shl',
            string='Data Shareholder Loan'
    )
    
    filter_option = fields.Selection([
        ('all', 'Tampilkan Semua'),
        # ('manual', 'Pilih Manual'),
    ], string='Filter')
    

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

    # Fields untuk Summary (Total)
    total_nominal_perjanjian = fields.Float(string='Total Nominal Sesuai Perjanjian', compute='_compute_total_nominal_perjanjian')
    total_nominal_dipinjamkan = fields.Float(string='Total Nominal Yang Dipinjamkan', compute='_compute_total_nominal_dipinjamkan')
    total_nominal_pengembalian = fields.Float(string='Total Nominal Pengembalian', compute='_compute_total_nominal_pengembalian')
    total_nominal_belum_dipinjamkan = fields.Float(string='Total Nominal yang Belum Dipinjamkan', compute='_compute_total_nominal_belum_dipinjamkan')
    total_nominal_kekurangan_pembayaran_shl = fields.Float(string='Total Nominal Kekurangan Pembayaran Angsuran SHL', compute='_compute_total_nominal_kekurangan_pembayaran_shl')   


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

    def _compute_total_nominal_perjanjian(self):
        for rec in self:
            # Hitung total nominal_perjanjian untuk semua record ShareholderLoan
            rec.total_nominal_perjanjian = sum(
                self.env['account.keuangan.shl'].search([]).mapped('nominal_perjanjian')
            )
    
    def _compute_total_nominal_dipinjamkan(self):
        for rec in self:
            # Hitung total nominal_dipinjamkan untuk semua record ShareholderLoan
            rec.total_nominal_dipinjamkan = sum(
                self.env['account.keuangan.shl'].search([]).mapped('nominal_dipinjamkan')
            )

    def _compute_total_nominal_pengembalian(self):
        for rec in self:
            # Hitung total nominal_pengembalian untuk semua record ShareholderLoan
            rec.total_nominal_pengembalian = sum(
                self.env['account.keuangan.shl'].search([]).mapped('nominal_pengembalian')
            )

    def _compute_total_nominal_belum_dipinjamkan(self):
        for rec in self:
            # Hitung total nominal_belum_dipinjamkan untuk semua record ShareholderLoan
            rec.total_nominal_belum_dipinjamkan = sum(
                self.env['account.keuangan.shl'].search([]).mapped('nominal_belum_dipinjamkan')
            )

    def _compute_total_nominal_kekurangan_pembayaran_shl(self):
        for rec in self:
            # Hitung total nominal_kekurangan_pembayaran_shl untuk semua record ShareholderLoan
            rec.total_nominal_kekurangan_pembayaran_shl = sum(
                self.env['account.keuangan.shl'].search([]).mapped('nominal_kekurangan_pembayaran_shl')
            )

    def action_preview(self):

        # # Jika user memilih tipe_notes, filter berdasarkan itu
        # if self.status_pencairan:
        #     domain = [('status_pencairan', '=', self.status_pencairan)]
        # else:
        #     domain = []  # Tidak ada filter → ambil semua data

        # records = self.env['account.keuangan.shl'].search(domain)
        records = self.env['account.keuangan.shl'].search([])
        
        
        # Kirimkan records yang ditemukan ke laporan
        return self.env.ref('agp_keuangan_ib.action_report_shl_preview').report_action(records)


    def action_export(self):

        # # Jika user memilih tipe_notes, filter berdasarkan itu
        # if self.status_pencairan:
        #     domain = [('status_pencairan', '=', self.status_pencairan)]
        # else:
        #     domain = []  # Tidak ada filter → ambil semua data

        # records = self.env['account.keuangan.shl'].search(domain)

        records = self.env['account.keuangan.shl'].search([])
        
        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Shareholder Loan')

        # Set format judul (bold, center)
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vleft', 'font_size': 14})

        # Tulis judul di baris pertama (row 0), kolom A sampai O (15 kolom)
        judul = 'SHAREHOLDER LOAN'
        sheet.merge_range(0, 0, 0, 9, judul, title_format)

        headers = ['NO', 'NOMOR SHAREHOLDER', 'TUJUAN', 'NOMOR SURAT PERJANJIAN', 'TANGGAL PERJANJIAN', 'NOMOR ADDENDUM', 'NOMINAL PERJANJIAN', 
                   'NOMINAL DIPINJAMKAN', 'NOMINAL PENGEMBALIAN', 'NOMINAL BELUM DIPINJAMKAN', 'NOMINAL KEKURANGAN PEMBAYARAN ANGSURAN SHL']
        
        header_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#ff8c00', 'text_wrap': True})  # Optional: header abu-abu
        total_format = workbook.add_format({'align': 'right', 'valign': 'vright', 'bold': True, 'bg_color': '#158e1b'})  # Optional: header abu-abu

        column_widths = [len(h) for h in headers]

        # Tulis header
        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        # Inisialisasi total untuk kolom yang diinginkan
        total_nominal_perjanjian = 0
        total_nominal_dipinjamkan = 0
        total_nominal_pengembalian = 0
        total_nominal_belum_dipinjamkan = 0
        total_nominal_kekurangan_pembayaran_shl = 0


        # Tulis data
        for row_num, record in enumerate(records, start=3):
            sheet.write(row_num, 0, row_num - 2)

            tanggal_perjanjian = record.tanggal_perjanjian.strftime('%d %b %Y').upper() if record.tanggal_perjanjian else ''
            nomor_addendum_str = ', '.join(record.nomor_addendum.mapped('no_adddendum')) if record.nomor_addendum else ''
            
            nominal_perjanjian = float(record.nominal_perjanjian) if record.nominal_perjanjian else 0
            nominal_dipinjamkan = float(record.nominal_dipinjamkan) if record.nominal_dipinjamkan else 0
            nominal_pengembalian = float(record.nominal_pengembalian) if record.nominal_pengembalian else 0
            nominal_belum_dipinjamkan = float(record.nominal_belum_dipinjamkan) if record.nominal_belum_dipinjamkan else 0
            nominal_kekurangan_pembayaran_shl = float(record.nominal_kekurangan_pembayaran_shl) if record.nominal_kekurangan_pembayaran_shl else 0
            
            total_nominal_perjanjian += nominal_perjanjian
            total_nominal_dipinjamkan += nominal_dipinjamkan
            total_nominal_pengembalian += nominal_pengembalian
            total_nominal_belum_dipinjamkan += nominal_belum_dipinjamkan
            total_nominal_kekurangan_pembayaran_shl += nominal_kekurangan_pembayaran_shl


            row_data = [
                str(row_num - 2),
                record.name or '',
                record.tujuan or '',
                record.nomor_perjanjian_id.name or '',
                tanggal_perjanjian,
                nomor_addendum_str,                
                "{:,.0f}".format(nominal_perjanjian),
                "{:,.0f}".format(nominal_dipinjamkan),
                "{:,.0f}".format(nominal_pengembalian),
                "{:,.0f}".format(nominal_belum_dipinjamkan),
                "{:,.0f}".format(nominal_kekurangan_pembayaran_shl),
            ]

            # Define format styles
            align_left_format = workbook.add_format({'align': 'left'})
            align_center_format = workbook.add_format({'align': 'center'})
            align_right_format = workbook.add_format({'align': 'right'})

            column_formats = [
                align_center_format,  # NO
                align_center_format,  # NOMOR SHAREHOLDER
                align_left_format,    # TUJUAN
                align_left_format,    # NOMOR SURAT PERJANJIAN
                align_center_format,  # TANGGAL PERJANJIAN
                align_left_format,    # NOMOR ADDENDUM
                align_right_format,   # NOMINAL PERJANJIAN
                align_right_format,   # NOMINAL DIPINJAMKAN
                align_right_format,   # NOMINAL PENGEMBALIAN
                align_right_format,   # NOMINAL BELUM DIPINJAMKAN
                align_right_format,   # NOMINAL KEKURANGAN PEMBAYARAN ANGSURAN SHL
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
                sheet.write(total_row, col_num, "{:,.0f}".format(total_nominal_perjanjian), total_format)  # Total nominal jaminan
            elif col_num == 7:  
                sheet.write(total_row, col_num, "{:,.0f}".format(total_nominal_dipinjamkan), total_format)  # Total biaya
            elif col_num == 8:  
                sheet.write(total_row, col_num, "{:,.0f}".format(total_nominal_pengembalian), total_format)  # Total dana kembali
            elif col_num == 9: 
                sheet.write(total_row, col_num, "{:,.0f}".format(total_nominal_belum_dipinjamkan), total_format)  # Total dana kembali
            elif col_num == 10: 
                sheet.write(total_row, col_num, "{:,.0f}".format(total_nominal_kekurangan_pembayaran_shl), total_format)  # Total dana kembali
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
            'name': 'Shareholder Loan.xlsx',  # Nama file yang diunduh
            'type': 'binary',
            'datas': file_data,  # Menyimpan file yang sudah di-encode dalam base64
            'store_fname': 'export_shareholder_loan.xlsx',
            'res_model': 'account.keuangan.shl',
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
        # domain = []
        # if self.tipe_notes:
        #     domain.append(('tipe_notes', '=', self.tipe_notes))

        # records = self.env['account.keuangan.sinking'].search(domain)

        records = self.env['account.keuangan.shl'].search([])

        result = []

        for idx, rec in enumerate(records, start=1):  # mulai dari 1

            result.append({
                'no': idx,
                'name': rec.name or '',
                'tujuan': rec.tujuan or '',
                'nomor_perjanjian': rec.nomor_perjanjian_id.name or '',
                'tanggal_perjanjian': format_date(rec.tanggal_perjanjian, format='d MMMM y', locale='id') if rec.tanggal_perjanjian else '',
                'nomor_addendum': ', '.join(rec.nomor_addendum.mapped('no_adddendum')) if rec.nomor_addendum else '',
                'nominal_perjanjian': "{:,.0f}".format(rec.nominal_perjanjian or 0.0),
                'nominal_dipinjamkan': "{:,.0f}".format(rec.nominal_dipinjamkan or 0.0),
                'nominal_pengembalian': "{:,.0f}".format(rec.nominal_pengembalian or 0.0),
                'nominal_belum_dipinjamkan': "{:,.0f}".format(rec.nominal_belum_dipinjamkan or 0.0),
                'nominal_kekurangan_pembayaran_shl': "{:,.0f}".format(rec.nominal_kekurangan_pembayaran_shl or 0.0),
            })
        
        for res in result : 
           print("RECORDS =", records)
           print("RESULT =", res)
 
        return result
    

    def action_print_pdf(self):
        
        records = self.shl_ids

        record_dicts = self.get_records_dict()


        data = {
            'objects': record_dicts,
        }

        # print("RECORDS =", records)
        # print("DATA =", data)

        return self.env.ref('agp_report_py3o.shl_py3o').report_action(
            records,  # PENTING! harus record dari model bank garansi
            data={
            'objects': record_dicts,
        })   