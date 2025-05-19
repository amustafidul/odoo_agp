import io
import xlsxwriter
from odoo import models, fields, api
from odoo.tools import pycompat
import base64
from babel.dates import format_date


class DepositoExportWizard(models.TransientModel):
    _name = 'deposito.export.wizard'
    _description = 'Wizard Export Deposito'

    deposito_ids = fields.Many2many(
        comodel_name='account.keuangan.deposito',
        string='Data Deposito'
    )

    status_pencairan = fields.Selection([
        ('aktif', 'Sudah'),
        ('non_aktif', 'Belum'),
    ], string="Status Pencairan", store=True, tracking=True)

    status_pencairan_display = fields.Char(string="Status Pencairan (Display)", compute="_compute_status_pencairan_display", store=True)
    
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

    total_saldo = fields.Float(string='Total Saldo', compute='_compute_saldo', store=True, tracking=True)


    # @api.model
    # def create(self, vals):
    #     # Automatically set the branch based on the logged-in user
    #     vals['branch_id'] = self.env.user.branch_id.id  # Assuming the user has a field branch_id
    #     return super(Deposito, self).create(vals)

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

    @api.depends('status_pencairan')
    def _compute_status_pencairan_display(self):
        for rec in self:
            status_dict = dict(self._fields['status_pencairan'].selection)
            rec.status_pencairan_display = status_dict.get(rec.status_pencairan, '')

    @api.depends('status_pencairan')
    def _compute_saldo(self):
        for wizard in self:
            domain = []
            if wizard.status_pencairan:
                domain.append(('status_pencairan', '=', wizard.status_pencairan))

            records = self.env['account.keuangan.deposito'].search(domain)
            wizard.total_saldo = sum(records.mapped('saldo'))
            

    def get_records_dict(self):
        # Jika user memilih tipe_notes, filter berdasarkan itu
        if self.status_pencairan:
            domain = [('status_pencairan', '=', self.status_pencairan)]
        else:
            domain = []  # Tidak ada filter → ambil semua data

        records = self.env['account.keuangan.deposito'].search(domain)

        result = []

        for idx, rec in enumerate(records, start=1):  # mulai dari 1

            result.append({
                'no': idx,
                'name': rec.name or '',
                'status_pencairan': rec.status_pencairan or '',
                'no_rek': rec.no_rek or '',
                'billyet': rec.billyet or '',
                'periode_produk': rec.periode_produk_id.name or '',
                'tanggal_deposito': format_date(rec.tanggal_deposito, format='d MMMM y', locale='id') if rec.tanggal_deposito else '',
                'tanggal_jatuh_tempo': format_date(rec.tanggal_jatuh_tempo, format='d MMMM y', locale='id') if rec.tanggal_jatuh_tempo else '',
                'jangka_waktu': rec.jangka_waktu or '',
                'tanggal_pencairan': format_date(rec.tanggal_pencairan, format='d MMMM y', locale='id') if rec.tanggal_pencairan else '',
                'tipe_produk': rec.tipe_produk_display or '',
                'status_tergadai': rec.status_tergadai_display or '',
                'nama_bank_garansi': rec.nama_bank_garansi.name or '',
                'no_gadai': rec.no_gadai or '',
                'branch_id': ', '.join(rec.branch_id.mapped('name')),
                'bank_pembuka': rec.no_gadai or '',
                'saldo': "{:,.0f}".format(rec.saldo or 0.0),
                'presentase_bunga': rec.presentase_bunga or '',
                'status_pencairan': rec.status_pencairan_display or '',
                'keterangan': rec.keterangan or '',
                # 'total_deposito': "{:,.0f}".format(rec.total_deposito or 0.0),
                # 'total_biaya_admin': "{:,.0f}".format(rec.total_biaya_admin or 0.0),
                # 'total_saldo': "{:,.0f}".format(rec.total_saldo or 0.0),
            })
        
        for res in result : 
           print("RECORDS =", records)
           print("RESULT =", res)
 
        return result
    
   
    def action_print_pdf(self):
        
        records = self.deposito_ids

        record_dicts = self.get_records_dict()


        data = {
            'objects': record_dicts,
        }

        # print("RECORDS =", records)
        # print("DATA =", data)

        return self.env.ref('agp_report_py3o.deposito_py3o').report_action(
            records,  # PENTING! harus record dari model bank garansi
            data={
            'objects': record_dicts,
        })
    
    def action_preview(self):

        # Jika user memilih tipe_notes, filter berdasarkan itu
        if self.status_pencairan:
            domain = [('status_pencairan', '=', self.status_pencairan)]
        else:
            domain = []  # Tidak ada filter → ambil semua data

        records = self.env['account.keuangan.deposito'].search(domain)
        
        
        # Kirimkan records yang ditemukan ke laporan
        return self.env.ref('agp_keuangan_ib.action_report_deposito_html').report_action(records)


    def action_export(self):
        # Jika user memilih tipe_notes, filter berdasarkan itu
        if self.status_pencairan:
            domain = [('status_pencairan', '=', self.status_pencairan)]
        else:
            domain = []  # Tidak ada filter → ambil semua data

        records = self.env['account.keuangan.deposito'].search(domain) 

        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Deposito')

        # Set format judul (bold, center)
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vleft', 'font_size': 14})
        
        label = dict(self._fields['status_pencairan'].selection).get(self.status_pencairan, '')
        judul = f"STATUS PENCAIRAN = {label.upper()}"
        sheet.merge_range(0, 0, 0, 9, judul, title_format)

        headers = ['NO', 'NO. DEPOSITO', 'NO. REKENING', 'NO. BILLYET', 'PERIODE PRODUK', 'TANGGAL DEPOSITO', 
                   'TANGGAL JATUH TEMPO', 'JANGKA WAKTU (BULAN)', 'TANGGAL PENCAIRAN', 'TIPE PRODUK', 'STATUS TERGADAI', 'NAMA BANK GARANSI', 
                   'NO GADAI', 'NAMA CABANG', 'BANK CABANG PEMBUKA', 'SALDO', 'PRESENTASE BUNGA', 'STATUS PENCAIRAN', 'KETERANGAN']
        
        header_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#ff8c00', 'text_wrap': True})  # Optional: header abu-abu
        total_format = workbook.add_format({'align': 'right', 'valign': 'vright', 'bold': True, 'bg_color': '#158e1b'})  # Optional: header abu-abu

        column_widths = [len(h) for h in headers]
 
        # Tulis header
        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        total_saldo = 0

        # Tulis data
        for row_num, record in enumerate(records, start=3):

            tanggal_deposito = record.tanggal_deposito.strftime('%d %b %Y').upper() if record.tanggal_deposito else ''
            tanggal_jatuh_tempo = record.tanggal_jatuh_tempo.strftime('%d %b %Y').upper() if record.tanggal_jatuh_tempo else ''
            tanggal_pencairan = record.tanggal_pencairan.strftime('%d %b %Y').upper() if record.tanggal_pencairan else ''

            saldo = float(record.saldo) if record.saldo else 0

            total_saldo += saldo

            row_data = [
                row_num - 2,  # NO
                record.name or '',
                record.no_rek or '',
                record.billyet or '',
                record.periode_produk_id.name or '',
                tanggal_deposito,
                tanggal_jatuh_tempo,
                record.jangka_waktu or '',
                tanggal_pencairan,
                record.tipe_produk_display or '',
                record.status_tergadai_display or '',
                record.nama_bank_garansi.name if record.nama_bank_garansi else '',
                record.no_gadai or '',
                ', '.join(record.branch_id.mapped('name')),
                record.bank_pembuka or '',
                "{:,.0f}".format(saldo),
                record.presentase_bunga or '',
                record.status_pencairan_display or '',
                record.keterangan or ''
            ]

            # Define format styles
            align_left_format = workbook.add_format({'align': 'left'})
            align_center_format = workbook.add_format({'align': 'center'})
            align_right_format = workbook.add_format({'align': 'right'})

            column_formats = [
                align_center_format,  # NO
                align_left_format,    # NO. DEPOSITO
                align_left_format,    # NO. REKENING
                align_left_format,    # NO. BILLYET
                align_left_format,    # PERIODE PRODUK
                align_center_format,  # TANGGAL DEPOSITO
                align_center_format,  # TANGGAL JATUH TEMPO
                align_center_format,  # JANGKA WAKTU (BULAN)
                align_center_format,  # TANGGAL PENCAIRAN
                align_left_format,    # TIPE PRODUK
                align_left_format,    # STATUS TERGADAI
                align_left_format,    # NAMA BANK GARANSI
                align_left_format,    # NO GADAI
                align_left_format,    # NAMA CABANG
                align_left_format,    # BANK CABANG PEMBUKA
                align_right_format,   # SALDO
                align_left_format,    # PRESENTASE BUNGA
                align_left_format,    # STATUS PENCAIRAN
                align_left_format     # KETERANGAN
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
            if col_num == 1:  # Kolom 'JAMINAN BANK GARANSI'
                sheet.write(total_row, 1, 'TOTAL', total_format)            
            elif col_num == 15:  # Kolom 'JAMINAN BANK GARANSI'
                sheet.write(total_row, col_num, "{:,.0f}".format(total_saldo), total_format)  # Total nominal jaminan
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
            'name': 'Deposito.xlsx',  # Nama file yang diunduh
            'type': 'binary',
            'datas': file_data,  # Menyimpan file yang sudah di-encode dalam base64
            'store_fname': 'deposito.xlsx',
            'res_model': 'account.keuangan.deposito',
            'res_id': self.id,
        })
        
        output.close()

        # Kembalikan URL untuk download attachment
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }