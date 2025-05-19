import io
import xlsxwriter
from odoo import models, fields, api
from odoo.tools import pycompat
import base64
from babel.dates import format_date


class NpExportWizard(models.TransientModel):
    _name = 'np.export.wizard'
    _description = 'Wizard Export National Pooling'

    np_ids = fields.Many2many(
            comodel_name='account.keuangan.np',
            string='Data National Pooling',
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

    summary_sinking_fund = fields.Float(string='Total Penerimaan / Pengeluaran Sinking Fund', compute='_compute_summary_sinking_fund')
    summary_deposito = fields.Float(string='Total Pembuatan/Pencairan Deposito', compute='_compute_summary_deposito')
    summary_pendapatan = fields.Float(string='Total Pendapatan', compute='_compute_summary_pendapatan')
    summary_biaya_admin = fields.Float(string='Total Pendapatan dan Biaya Administrasi Bank', compute='_compute_summary_biaya_admin')
    summary_saldo = fields.Float(string='Total Saldo', compute='_compute_summary_saldo')


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
    
    @api.depends()
    def _compute_summary_sinking_fund(self):
        for rec in self:
            rec.summary_sinking_fund = sum(
                self.env['account.keuangan.np'].search([]).mapped('total_sinking_fund')
            ) 
            
    @api.depends()
    def _compute_summary_deposito(self):
        for rec in self:
            rec.summary_deposito = sum(
                self.env['account.keuangan.np'].search([]).mapped('total_deposito')
            ) 
    
    @api.depends()
    def _compute_summary_pendapatan(self):
        for rec in self:
            rec.summary_pendapatan = sum(
                self.env['account.keuangan.np'].search([]).mapped('total_pendapatan')
            ) 

    @api.depends()    
    def _compute_summary_biaya_admin(self):
        for rec in self:
            rec.summary_biaya_admin = sum(
                self.env['account.keuangan.np'].search([]).mapped('total_biaya_admin')
            )

    @api.depends()
    def _compute_summary_saldo(self):
        for rec in self:
            rec.summary_saldo = sum(
                self.env['account.keuangan.np'].search([]).mapped('total_saldo')
            )


    def action_preview(self):

        # # Jika user memilih tipe_notes, filter berdasarkan itu
        # if self.status_pencairan:
        #     domain = [('status_pencairan', '=', self.status_pencairan)]
        # else:
        #     domain = []  # Tidak ada filter → ambil semua data

        # records = self.env['account.keuangan.shl'].search(domain)
        records = self.env['account.keuangan.np'].search([])
        
        
        # Kirimkan records yang ditemukan ke laporan
        return self.env.ref('agp_keuangan_ib.action_report_np_preview').report_action(records)


    def action_export(self):

        # # Jika user memilih tipe_notes, filter berdasarkan itu
        # if self.status_pencairan:
        #     domain = [('status_pencairan', '=', self.status_pencairan)]
        # else:
        #     domain = []  # Tidak ada filter → ambil semua data

        # records = self.env['account.keuangan.shl'].search(domain)

        records = self.env['account.keuangan.np'].search([])
        
        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('National Pooling')

        # Set format judul (bold, center)
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vleft', 'font_size': 14})

        # Tulis judul di baris pertama (row 0), kolom A sampai O (15 kolom)
        judul = 'NATIONAL POOLING'
        sheet.merge_range(0, 0, 0, 9, judul, title_format)

        headers = ['NO', 'NOMOR NATIONAL POOLING', 'URAIAN', 'BANK', 'REKENING', 'MATURITY DATE', 'TOTAL PENERIMAAN / PENGELUARAN SINKING FUND', 
                   'TOTAL PEMBUATAN / PENCAIRAN DEPOSITO', 'TOTAL PENDAPATAN', 'TOTAL PENDAPATAN DAN BIAYA ADMINISTRASI BANK', 'TOTAL SALDO']
        
        header_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#ff8c00', 'text_wrap': True})  # Optional: header abu-abu
        total_format = workbook.add_format({'align': 'right', 'valign': 'vright', 'bold': True, 'bg_color': '#158e1b'})  # Optional: header abu-abu

        column_widths = [len(h) for h in headers]

        # Tulis header
        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        # Inisialisasi total untuk kolom yang diinginkan
        summary_total_sinking_fund = 0
        summary_total_deposito = 0
        summary_total_pendapatan = 0
        summary_total_biaya_admin = 0
        summary_total_saldo = 0


        # Tulis data
        for row_num, record in enumerate(records, start=3):
            sheet.write(row_num, 0, row_num - 2)

            maturity_date = record.maturity_date.strftime('%d %b %Y').upper() if record.maturity_date else ''
            
            total_sinking_fund = float(record.total_sinking_fund) if record.total_sinking_fund else 0
            total_deposito = float(record.total_deposito) if record.total_deposito else 0
            total_pendapatan = float(record.total_pendapatan) if record.total_pendapatan else 0
            total_biaya_admin = float(record.total_biaya_admin) if record.total_biaya_admin else 0
            total_saldo = float(record.total_saldo) if record.total_saldo else 0
            
            summary_total_sinking_fund += total_sinking_fund
            summary_total_deposito += total_deposito
            summary_total_pendapatan += total_pendapatan
            summary_total_biaya_admin += total_biaya_admin
            summary_total_saldo += total_saldo


            row_data = [
                str(row_num - 2),
                record.name or '',
                record.uraian_pooling or '',
                record.bank or '',
                record.rekening or '',
                maturity_date,                
                "{:,.0f}".format(total_sinking_fund),
                "{:,.0f}".format(total_deposito),
                "{:,.0f}".format(total_pendapatan),
                "{:,.0f}".format(total_biaya_admin),
                "{:,.0f}".format(total_saldo),
            ]

            # Define format styles
            align_left_format = workbook.add_format({'align': 'left'})
            align_center_format = workbook.add_format({'align': 'center'})
            align_right_format = workbook.add_format({'align': 'right'})

            column_formats = [
                align_center_format,  # NO
                align_center_format,  # NOMOR NATIONAL POOLING
                align_left_format,    # URAIAN
                align_left_format,    # BANK
                align_left_format,    # REKENING
                align_center_format,  # MATURITY DATE
                align_right_format,   # TOTAL PENERIMAAN / PENGELUARAN SINKING FUND
                align_right_format,   # TOTAL PEMBUATAN / PENCAIRAN DEPOSITO
                align_right_format,   # TOTAL PENDAPATAN
                align_right_format,   # TOTAL PENDAPATAN DAN BIAYA ADMINISTRASI BANK
                align_right_format,   # TOTAL SALDO
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
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_total_sinking_fund), total_format)  # Total nominal jaminan
            elif col_num == 7:  
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_total_deposito), total_format)  # Total biaya
            elif col_num == 8:  
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_total_pendapatan), total_format)  # Total dana kembali
            elif col_num == 9: 
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_total_biaya_admin), total_format)  # Total dana kembali
            elif col_num == 10: 
                sheet.write(total_row, col_num, "{:,.0f}".format(summary_total_saldo), total_format)  # Total dana kembali
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
            'name': 'National Pooling.xlsx',  # Nama file yang diunduh
            'type': 'binary',
            'datas': file_data,  # Menyimpan file yang sudah di-encode dalam base64
            'store_fname': 'export_national_pooling_.xlsx',
            'res_model': 'account.keuangan.np',
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

        records = self.env['account.keuangan.np'].search([])

        result = []

        for idx, rec in enumerate(records, start=1):  # mulai dari 1

            result.append({
                'no': idx,
                'name': rec.name or '',
                'uraian': rec.uraian_pooling or '',
                'bank': rec.bank or '',
                'rekening': rec.rekening or '',
                'maturity_date': format_date(rec.maturity_date, format='d MMMM y', locale='id') if rec.maturity_date else '',
                'total_sinking_fund': "{:,.0f}".format(rec.total_sinking_fund or 0.0),
                'total_deposito': "{:,.0f}".format(rec.total_deposito or 0.0),
                'total_pendapatan': "{:,.0f}".format(rec.total_pendapatan or 0.0),
                'total_biaya_admin': "{:,.0f}".format(rec.total_biaya_admin or 0.0),
                'total_saldo': "{:,.0f}".format(rec.total_saldo or 0.0),
            })
        
        for res in result : 
           print("RECORDS =", records)
           print("RESULT =", res)
 
        return result
    

    def action_print_pdf(self):
        
        records = self.np_ids

        record_dicts = self.get_records_dict()


        data = {
            'objects': record_dicts,
        }

        # print("RECORDS =", records)
        # print("DATA =", data)

        return self.env.ref('agp_report_py3o.np_py3o').report_action(
            records,  # PENTING! harus record dari model bank garansi
            data={
            'objects': record_dicts,
        })   