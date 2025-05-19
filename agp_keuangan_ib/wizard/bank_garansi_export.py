import io
import xlsxwriter
from odoo import models, fields, api
from odoo.tools import pycompat
import base64
from babel.dates import format_date


class BankGaransiExportWizard(models.TransientModel):
    _name = 'bank.garansi.export.wizard'
    _description = 'Wizard Export Bank Garansi'

    tipe_bank_garansi_id = fields.Many2one('account.keuangan.tipe.bank.garansi', string='Tipe Bank Garansi')
    bank_garansi_ids = fields.Many2many(
            comodel_name='account.keuangan.bank.garansi',
            string='Data Bank Garansi'
        )
    
    total_nominal_jaminan = fields.Float(string='Total Nominal Jaminan', compute='_compute_totals', store=False)
    total_biaya_asuransi = fields.Float(string='Total Biaya Asuransi', compute='_compute_totals', store=False)
    total_dana_kembali = fields.Float(string='Total Dana Kembali', compute='_compute_totals', store=False)

    # branch_id = fields.Many2one('res.branch', string='Nama Cabang', tracking=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

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

    @api.depends('tipe_bank_garansi_id')
    def _compute_totals(self):
        for wizard in self:
            domain = []
            if wizard.tipe_bank_garansi_id:
                domain.append(('tipe_bank_garansi_id', '=', wizard.tipe_bank_garansi_id.id))

            records = self.env['account.keuangan.bank.garansi'].search(domain)
            wizard.total_nominal_jaminan = sum(records.mapped('nominal_jaminan'))
            wizard.total_biaya_asuransi = sum(records.mapped('biaya_asuransi'))
            wizard.total_dana_kembali = sum(records.mapped('dana_kembali'))
            

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            res['bank_garansi_ids'] = [(6, 0, active_ids)]
        return res
    
    
    def action_export_bank_garansi(self):

        # Jika tipe_bank_garansi_id dipilih, filter berdasarkan tipe tersebut
        if self.tipe_bank_garansi_id:
            domain = [('tipe_bank_garansi_id', '=', self.tipe_bank_garansi_id.id)]
        else:
            domain = []  # Tidak ada filter jika tipe_bank_garansi_id kosong

        records = self.env['account.keuangan.bank.garansi'].search(domain)

        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Bank Garansi')

        # Set format judul (bold, center)
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vleft', 'font_size': 14})

        # Tulis judul di baris pertama (row 0), kolom A sampai O (15 kolom)
        # judul = self.tipe_bank_garansi_id.name.upper() if self.tipe_bank_garansi_id else ''
        judul = 'BANK GARANSI'
        sheet.merge_range(0, 0, 0, 14, judul, title_format)

        # Header
        # headers = ['NO', 'UNIT', 'PEMBERI KERJA', 'PEKERJAAN', 'NOMOR BANK GARANSI', 'TANGGAL TERBIT BANK GARANSI',
        #         'JAMINAN BANK GARANSI', 'MASA BERLAKU BANK GARANSI', 'JENIS BANK GARANSI', 'BANK', 'NAMA ASURANSI',
        #         'BIAYA', 'DANA YANG KEMBALI', 'JUMLAH JAMINAN', 'KETERANGAN']
        
        headers = ['NO', 'UNIT', 'PEMBERI KERJA', 'PEKERJAAN', 'NOMOR BANK GARANSI', 'TANGGAL TERBIT BANK GARANSI',
                'TIPE BANK GARANSI', 'JAMINAN BANK GARANSI', 'MASA BERLAKU BANK GARANSI', 'JENIS BANK GARANSI', 'BANK', 'NAMA ASURANSI',
                'BIAYA', 'DANA YANG KEMBALI', 'KETERANGAN']
        
        header_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'bg_color': '#ff8c00'})  # Optional: header abu-abu
        total_format = workbook.add_format({'align': 'right', 'valign': 'vright', 'bold': True, 'bg_color': '#158e1b'})  # Optional: header abu-abu

        # Untuk track panjang maksimum per kolom
        column_widths = [len(h) for h in headers]

        # Tulis header
        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        # Inisialisasi total untuk kolom yang diinginkan
        total_nominal_jaminan = 0
        total_biaya_asuransi = 0
        total_dana_kembali = 0

        # Tulis data
        for row_num, record in enumerate(records, start=3):
            # Format tanggal terbit bank garansi
            tanggal_bank_garansi = record.tanggal_bank_garansi.strftime('%d %b %Y').upper() if record.tanggal_bank_garansi else ''

            # Format nominal jaminan
            # Pastikan nominal_jaminan, biaya, dan dana_kembali bertipe numerik
            nominal_jaminan = float(record.nominal_jaminan) if record.nominal_jaminan else 0
            biaya_asuransi = float(record.biaya_asuransi) if record.biaya_asuransi else 0
            dana_kembali = float(record.dana_kembali) if record.dana_kembali else 0

            total_nominal_jaminan += nominal_jaminan
            total_biaya_asuransi += biaya_asuransi
            total_dana_kembali += dana_kembali

            # Format masa berlaku: mulai - akhir
            if record.mulai_garansi and record.akhir_garansi:
                mulai = record.mulai_garansi.strftime('%d %B %Y').upper()
                akhir = record.akhir_garansi.strftime('%d %B %Y').upper()
                masa_berlaku = f"{mulai} - {akhir}"
            else:
                masa_berlaku = ''

            # Susun data row
            row_data = [
                str(row_num - 2),
                ', '.join(record.sub_branch_ids.mapped('name')) or '',
                record.pemberi_kerja or '',
                record.pekerjaan or '',
                record.name or '',
                tanggal_bank_garansi,
                record.tipe_bank_garansi_id.name if record.tipe_bank_garansi_id else '',
                "{:,.0f}".format(nominal_jaminan),
                masa_berlaku,
                record.jenis_bank_garansi_id.name if record.jenis_bank_garansi_id else '',
                record.bank_cabang or '',
                record.nama_asuransi or '',
                "{:,.0f}".format(biaya_asuransi),
                "{:,.0f}".format(dana_kembali),            
                # "{:,.0f}".format(record.jumlah_jaminan) if record.jumlah_jaminan else '',
                record.keterangan or '',
            ]

            # Define format styles
            align_left_format = workbook.add_format({'align': 'left'})
            align_center_format = workbook.add_format({'align': 'center'})
            align_right_format = workbook.add_format({'align': 'right'})

            column_formats = [
                align_center_format,
                align_left_format,
                align_left_format,
                align_left_format,
                align_center_format,
                align_center_format,
                align_right_format,
                align_right_format,
                align_center_format,
                align_center_format,
                align_center_format,
                align_right_format,
                align_right_format,
                align_right_format,
                # align_left_format,
                align_left_format,
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
            elif col_num == 7:  # Kolom 'JAMINAN BANK GARANSI'
                sheet.write(total_row, col_num, "{:,.0f}".format(total_nominal_jaminan), total_format)  # Total nominal jaminan
            elif col_num == 12:  # Kolom 'BIAYA'
                sheet.write(total_row, col_num, "{:,.0f}".format(total_biaya_asuransi), total_format)  # Total biaya
            elif col_num == 13:  # Kolom 'DANA YANG KEMBALI'
                sheet.write(total_row, col_num, "{:,.0f}".format(total_dana_kembali), total_format)  # Total dana kembali
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
            'name': 'Export_Bank_Garansi.xlsx',  # Nama file yang diunduh
            'type': 'binary',
            'datas': file_data,  # Menyimpan file yang sudah di-encode dalam base64
            'store_fname': 'export_bank_garansi.xlsx',
            'res_model': 'account.keuangan.bank.garansi',
            'res_id': self.id,
        })
        
        output.close()

        # Kembalikan URL untuk download attachment
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }
    

    def action_print_report(self):
    # Jika user memilih tipe_bank_garansi_id, filter berdasarkan itu
        if self.tipe_bank_garansi_id:
            domain = [('tipe_bank_garansi_id', '=', self.tipe_bank_garansi_id.id)]
        else:
            domain = []  # Tidak ada filter → ambil semua data

        records = self.env['account.keuangan.bank.garansi'].search(domain)

        return self.env.ref('agp_keuangan_ib.action_report_bank_garansi_html').report_action(records)



    def get_records_dict(self):
        domain = []  # Mulai dengan domain kosong

        # Jika tipe_bank_garansi_id dipilih, tambahkan filter berdasarkan tipe tersebut
        if self.tipe_bank_garansi_id:
            domain.append(('tipe_bank_garansi_id', '=', self.tipe_bank_garansi_id.id))

        # Mencari records berdasarkan domain yang sudah diatur
        records = self.env['account.keuangan.bank.garansi'].search(domain)

        result = []

        for idx, rec in enumerate(records, start=1):  # mulai dari 1

            result.append({
                'no': idx,
                'sub_branch': ', '.join(rec.sub_branch_ids.mapped('name')),
                'pemberi_kerja': rec.pemberi_kerja or '',
                'pekerjaan': rec.pekerjaan or '',
                'name': rec.name or '',
                'tanggal_bank_garansi': format_date(rec.tanggal_bank_garansi, format='d MMMM y', locale='id') if rec.tanggal_bank_garansi else '',
                'tipe_bank_garansi_id': rec.tipe_bank_garansi_id.name or 'BANK GARANSI',
                'nominal_jaminan': "{:,.0f}".format(rec.nominal_jaminan or 0.0),
                'mulai_garansi': format_date(rec.mulai_garansi, format='d MMMM y', locale='id') if rec.mulai_garansi else '',
                'akhir_garansi': format_date(rec.akhir_garansi, format='d MMMM y', locale='id') if rec.akhir_garansi else '',
                'jenis_bank_garansi': rec.jenis_bank_garansi_id.name if rec.jenis_bank_garansi_id else '',
                'bank_cabang': rec.bank_cabang or '',
                'nama_asuransi': rec.nama_asuransi or '',
                'biaya_asuransi': "{:,.0f}".format(rec.biaya_asuransi or 0.0),
                'dana_kembali': "{:,.0f}".format(rec.dana_kembali or 0.0),
                'keterangan': rec.keterangan or '',
            })
        
        for res in result : 
           print("RECORDS =", records)
           print("RESULT =", res)
 
        return result
    
   
    def action_print_pdf(self):
        
        records = self.bank_garansi_ids

        record_dicts = self.get_records_dict()


        data = {
            'objects': record_dicts,
        }

        # print("RECORDS =", records)
        # print("DATA =", data)

        return self.env.ref('agp_report_py3o.bank_garansi_py3o').report_action(
            records,  # PENTING! harus record dari model bank garansi
            data={
            'objects': record_dicts,
        })