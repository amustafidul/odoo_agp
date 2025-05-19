from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class AnggaranHarian(models.Model):


    _name = 'account.keuangan.anggaran.harian'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Anggaran Harian'

    name = fields.Char(string='Judul Anggaran Harian')
    tanggal_anggaran = fields.Date(string='Tanggal Anggaran', required=True, tracking=True)
    saldo_awal = fields.Float(string='Saldo Awal', store=True, tracking=True)
    saldo_akhir = fields.Float(string='Saldo Akhir', compute ='_compute_saldo_akhir', store=True, tracking=True)
    jumlah = fields.Float(string='Jumlah Penggunaan', compute='_compute_nominal', store=True, tracking=True)
    disiapkan = fields.Char(string='Disiapkan')
    diketahui = fields.Char(string='Diketahui')
    disetujui = fields.Char(string='Disetujui')
    noted = fields.Text(string='Noted')

    anggaran_harian_line_ids = fields.One2many('account.keuangan.anggaran.harian.line', 'anggaran_harian_id', string='Anggaran Harian Lines')

    total_penerimaan = fields.Float(string='Total Penerimaan', compute='_compute_totals', store=True)
    total_pengeluaran = fields.Float(string='Total Pengeluaran', compute='_compute_totals', store=True)


    jumlah_bni_pooling_operasional = fields.Float(compute='_compute_jumlah_bni_pooling_operasional', store=True, string='Jumlah BNI Pooling Operasional')
    jumlah_bni_operasional_bank_saving = fields.Float(compute='_compute_jumlah_bni_operasional_bank_saving', store=True, string='Jumlah Total BNI Pooling')
    jumlah_bni_saving_bank_lainnya = fields.Float(compute='_compute_jumlah_bni_saving_bank_lainnya', store=True, string='Jumlah Total BNI Pooling Bank Saving + Bank Lainnya')
    jumlah_penerimaan_bank = fields.Float(compute='_compute_penerimaan_bank', store=True, string='Penerimaan Bank')
    jumlah_pengeluaran_bank = fields.Float(compute='_compute_pengeluaran_bank', store=True, string='Pengeluaran Bank')
    total_saldo = fields.Float(compute='_compute_total_saldo', store=True, string='Total Saldo')
    sisa_saldo_bank = fields.Float(compute='_compute_sisa_saldo_bank', store=True, string='Sisa Saldo Bank')

    # Computed fields untuk perhitungan dari baris (line)
    penerimaan_cash_pooling_amount = fields.Float(compute='_compute_penerimaan_cash_pooling', store=True, string='Penerimaan Cash Pooling')
    penerimaan_pihak_ketiga_amount = fields.Float(compute='_compute_penerimaan_pihak_ketiga', store=True, string='Penerimaan Pihak Ketiga')
    bank_saving_amount = fields.Float(compute='_compute_bank_saving', store=True, string='Bank Saving')
    bank_lainnya_amount = fields.Float(compute='_compute_bank_lainnya', store=True, string='Bank Lainnya')
    kebutuhan_kas_mingguan_cabang_amount = fields.Float(compute='_compute_kebutuhan_kas_mingguan_cabang', store=True, string='Kebutuhan Kas Mingguan Cabang')
    pembayaran_kepada_pihak_ketiga_amount = fields.Float(compute='_compute_pembayaran_kepada_pihak_ketiga', store=True, string='Pembayaran Kepada Pihak Ketiga')
    biaya_umum_amount = fields.Float(compute='_compute_biaya_umum', store=True, string='Biaya Umum')
    lainnya_amount = fields.Float(compute='_compute_lainnya', store=True, string='Lainnya')

    
    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_penerimaan_cash_pooling(self):
        for record in self:
            record.penerimaan_cash_pooling_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'penerimaan_cash_pooling')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_penerimaan_pihak_ketiga(self):
        for record in self:
            record.penerimaan_pihak_ketiga_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'penerimaan_pihak_ketiga')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_bank_saving(self):
        for record in self:
            record.bank_saving_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'bank_saving')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_bank_lainnya(self):
        for record in self:
            record.bank_lainnya_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'bank_lainnya')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_kebutuhan_kas_mingguan_cabang(self):
        for record in self:
            record.kebutuhan_kas_mingguan_cabang_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'kebutuhan_kas_mingguan_cabang')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_pembayaran_kepada_pihak_ketiga(self):
        for record in self:
            record.pembayaran_kepada_pihak_ketiga_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'pembayaran_kepada_pihak_ketiga')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_biaya_umum(self):
        for record in self:
            record.biaya_umum_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'biaya_umum')

    @api.depends('anggaran_harian_line_ids.type_transaksi')
    def _compute_lainnya(self):
        for record in self:
            record.lainnya_amount = sum(line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'lainnya')


    @api.depends('penerimaan_cash_pooling_amount', 'penerimaan_pihak_ketiga_amount')
    def _compute_jumlah_bni_pooling_operasional(self):
        for record in self:
            record.jumlah_bni_pooling_operasional = record.penerimaan_cash_pooling_amount + record.penerimaan_pihak_ketiga_amount


    @api.depends('jumlah_bni_pooling_operasional', 'bank_saving_amount')
    def _compute_jumlah_bni_operasional_bank_saving(self):
        for record in self:
            record.jumlah_bni_operasional_bank_saving = record.jumlah_bni_pooling_operasional + record.bank_saving_amount

    @api.depends('jumlah_bni_operasional_bank_saving', 'bank_lainnya_amount')
    def _compute_jumlah_bni_saving_bank_lainnya(self):
        for record in self:
            record.jumlah_bni_saving_bank_lainnya = record.jumlah_bni_operasional_bank_saving + record.bank_lainnya_amount

    @api.depends('kebutuhan_kas_mingguan_cabang_amount', 'pembayaran_kepada_pihak_ketiga_amount', 'biaya_umum_amount')
    def _compute_pengeluaran_bank(self):
        for record in self:
            record.jumlah_pengeluaran_bank = (
                record.kebutuhan_kas_mingguan_cabang_amount +
                record.pembayaran_kepada_pihak_ketiga_amount +
                record.biaya_umum_amount
            )

    @api.depends('penerimaan_cash_pooling_amount', 'penerimaan_pihak_ketiga_amount', 'bank_saving_amount', 'bank_lainnya_amount')
    def _compute_penerimaan_bank(self):
        for record in self:
            record.jumlah_penerimaan_bank = (
                record.penerimaan_cash_pooling_amount +
                record.penerimaan_pihak_ketiga_amount +
                record.bank_saving_amount +
                record.bank_lainnya_amount 
            )
    
    @api.depends('saldo_awal', 'total_penerimaan')
    def _compute_total_saldo(self):
        for record in self:
            record.total_saldo = (
                record.saldo_awal +
                record.total_penerimaan)

    @api.depends('total_saldo', 'jumlah_pengeluaran_bank')
    def _compute_sisa_saldo_bank(self):
        for record in self:
            record.sisa_saldo_bank = record.total_saldo - record.jumlah_pengeluaran_bank

    @api.depends('anggaran_harian_line_ids.nominal', 'anggaran_harian_line_ids.type_transaksi')
    def _compute_totals(self):
        for record in self:
            record.total_penerimaan = sum(
                line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi in [
                    'penerimaan_cash_pooling', 
                    'penerimaan_pihak_ketiga', 
                    'bank_saving', 
                    'bank_lainnya'
                ]
            )
            record.total_pengeluaran = sum(
                line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi in [
                    'kebutuhan_kas_mingguan_cabang', 
                    'pembayaran_kepada_pihak_ketiga', 
                    'biaya_umum'
                ]
            )

    @api.depends('saldo_awal', 'total_penerimaan', 'total_pengeluaran', 'lainnya_amount', 'anggaran_harian_line_ids.nominal', 'anggaran_harian_line_ids.type_transaksi')
    def _compute_saldo_akhir(self):
        for record in self:
            # total_lainnya = sum(
            #     line.nominal for line in record.anggaran_harian_line_ids if line.type_transaksi == 'lainnya'
            # )
            record.saldo_akhir = record.saldo_awal + record.total_penerimaan - record.total_pengeluaran + record.lainnya_amount


    @api.depends('total_penerimaan', 'total_pengeluaran')
    def _compute_nominal(self):
        for record in self:
            record.jumlah = record.total_penerimaan - record.total_pengeluaran

    def copy(self, default=None):
        # Menyimpan data default untuk duplikasi
        default = dict(default or {})
        default['name'] = f"{self.name} (Copy)"  # Mengubah nama record hasil duplikasi jika perlu
        
        # Mendapatkan baris (lines) yang terkait dengan anggaran_harian_line_ids
        anggaran_harian_lines = self.anggaran_harian_line_ids
        new_record = super().copy(default)  # Cukup gunakan super() untuk memanggil copy dari kelas induk

        # Duplicating related lines
        for line in anggaran_harian_lines:
            line.copy(default={'anggaran_harian_id': new_record.id})

        return new_record


    def export_to_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Anggaran Harian')

        # Menambahkan informasi di atas table sebagai judul
        sheet.write(0, 0, "Judul Anggaran Harian")
        sheet.write(0, 1, f"{self.name or ''}")

        # Menulis "Tanggal Anggaran" di kolom 0, dan tanggal anggaran di kolom 1
        sheet.write(1, 0, "Tanggal Anggaran")
        sheet.write(1, 1, f"{self.tanggal_anggaran.strftime('%d/%m/%Y') if self.tanggal_anggaran else ''}")

        # Menulis "Saldo Awal" di kolom 0, dan saldo awal di kolom 1
        sheet.write(2, 0, "Saldo Awal")
        sheet.write(2, 1, f"{self.saldo_awal if self.saldo_awal else ''}")

        # Menulis "Jumlah Penggunaan" di kolom 0, dan jumlah penggunaan di kolom 1
        sheet.write(3, 0, "Jumlah Penggunaan")
        sheet.write(3, 1, f"{self.jumlah if self.jumlah else ''}")

        # Menulis "Saldo Akhir" di kolom 0, dan saldo akhir di kolom 1
        sheet.write(4, 0, "Saldo Akhir")
        sheet.write(4, 1, f"{self.saldo_akhir if self.saldo_akhir else ''}")

         # Format untuk header (bold dan center)
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})

        # Format untuk angka dalam rupiah
        rupiah_format = workbook.add_format({'num_format': '#,##0'})

        # Menambahkan header untuk data tabel
        headers = ['No', 'Tipe Transaksi', 'Deskripsi', 'Nominal']
        for col, header in enumerate(headers):
            sheet.write(6, col, header, header_format) 
        
        # Mengatur lebar kolom untuk setiap header
        column_widths = [5, 40, 30, 20]  # Adjust widths as needed
        for col_num, width in enumerate(column_widths):
            sheet.set_column(col_num, col_num, width)

        # Menambahkan data untuk setiap baris 'sinking_line_ids'
        for row, line in enumerate(self.anggaran_harian_line_ids, start=7):
            type_transaksi_label = dict(line._fields['type_transaksi'].selection).get(line.type_transaksi, 'Unknown')

            # Menulis data ke sheet
            sheet.write(row, 0, line.no)            
            sheet.write(row, 1, type_transaksi_label)            
            sheet.write(row, 2, line.deskripsi)
            sheet.write(row, 3, line.nominal, rupiah_format)
        
            row += 1

        # Selesaikan dan simpan file
        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Buat attachment dari file
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.name}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'store_fname': f'{self.name}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'account.keuangan.anggaran.harian',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class AnggaranHarian(models.Model):
    _name = 'account.keuangan.anggaran.harian.line'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Anggaran Harian Line'


    anggaran_harian_id = fields.Many2one(
        'account.keuangan.anggaran.harian',
        required=True)

    deskripsi = fields.Text(string='Deskripsi', tracking=True)
    nominal = fields.Float(string='Nominal', tracking=True)

    type_transaksi = fields.Selection(selection=[
        ('penerimaan_cash_pooling', 'PENERIMAAN CASH POOLING'),
        ('penerimaan_pihak_ketiga', 'PENERIMAAN PIHAK KE III'),
        ('bank_saving', 'BANK SAVING'),
        ('bank_lainnya', 'BANK LAINNYA'),
        ('kebutuhan_kas_mingguan_cabang', 'KEBUTUHAN KAS MINGGUAN CABANG'),
        ('pembayaran_kepada_pihak_ketiga', 'PEMBAYARAN KEPADA PIHAK KE III'),
        ('biaya_umum', 'BIAYA UMUM'),
        ('lainnya', 'BANK NATIONAL POOLING, MTN DAN SINKING FUND '),
    ], string='Tipe Transaksi', store= True, tracking=True)

    no = fields.Integer(string="No", compute="_compute_no")

    bank_account_ids = fields.Many2one('res.partner.bank', string='Bank Account')
    bank_account_name = fields.Char(string='Bank Account Name', related='bank_account_ids.acc_number', store=True)

    show_bank_account = fields.Boolean(string='Show Bank Account', compute='_compute_show_bank_account')

    @api.depends('type_transaksi')
    def _compute_show_bank_account(self):
        bank_related_types = [
            'bank_saving',
            'bank_lainnya',
            'penerimaan_cash_pooling',
            'penerimaan_pihak_ketiga',
            'pembayaran_kepada_pihak_ketiga',
            'lainnya'
        ]
        for record in self:
            record.show_bank_account = record.type_transaksi in bank_related_types


    def _compute_no(self):
        for index, record in enumerate(self, start=1):
            record.no = index

    # penerimaan_cash_pooling_amount = fields.Float(compute='_compute_penerimaan_cash_pooling', store=True, string='Penerimaan Cash Pooling')
    # penerimaan_pihak_ketiga_amount = fields.Float(compute='_compute_penerimaan_pihak_ketiga', store=True, string='Penerimaan Pihak Ketiga')
    # bank_saving_amount = fields.Float(compute='_compute_bank_saving', store=True, string='Bank Saving')
    # bank_lainnya_amount = fields.Float(compute='_compute_bank_lainnya', store=True, string='Bank Lainnya')
    # kebutuhan_kas_mingguan_cabang_amount = fields.Float(compute='_compute_kebutuhan_kas_mingguan_cabang', store=True, string='Kebutuhan Kas Mingguan Cabang')
    # pembayaran_kepada_pihak_ketiga_amount = fields.Float(compute='_compute_pembayaran_kepada_pihak_ketiga', store=True, string='Pembayaran Kepada Pihak Ketiga')
    # biaya_umum_amount = fields.Float(compute='_compute_biaya_umum', store=True, string='Biaya Umum')
    # lainnya_amount = fields.Float(compute='_compute_lainnya', store=True, string='Lainnya')


    # @api.depends('type_transaksi')
    # def _compute_penerimaan_cash_pooling(self):
    #     for record in self:
    #         if record.type_transaksi == 'penerimaan_cash_pooling':
    #             record.penerimaan_cash_pooling_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_penerimaan_pihak_ketiga(self):
    #     for record in self:
    #         if record.type_transaksi == 'penerimaan_pihak_ketiga':
    #             record.penerimaan_pihak_ketiga_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_bank_saving(self):
    #     for record in self:
    #         if record.type_transaksi == 'bank_saving':
    #             record.bank_saving_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_bank_lainnya(self):
    #     for record in self:
    #         if record.type_transaksi == 'bank_lainnya':
    #             record.bank_lainnya_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_kebutuhan_kas_mingguan_cabang(self):
    #     for record in self:
    #         if record.type_transaksi == 'kebutuhan_kas_mingguan_cabang':
    #             record.kebutuhan_kas_mingguan_cabang_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_pembayaran_kepada_pihak_ketiga(self):
    #     for record in self:
    #         if record.type_transaksi == 'pembayaran_kepada_pihak_ketiga':
    #             record.pembayaran_kepada_pihak_ketiga_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_biaya_umum(self):
    #     for record in self:
    #         if record.type_transaksi == 'biaya_umum':
    #             record.biaya_umum_amount = record.nominal

    # @api.depends('type_transaksi')
    # def _compute_lainnya(self):
    #     for record in self:
    #         if record.type_transaksi == 'lainnya':
    #             record.lainnya_amount = record.nominal



