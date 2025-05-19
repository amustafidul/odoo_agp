from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class TagihanRutin(models.Model):
    _name = 'tagihan.rutin'
    _description = 'Tagihan Rutin'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Deskripsi", required=True, tracking=True)
    nominal_pinjaman2 = fields.Float(string="Nominal Pinjaman", tracking=True)
    bunga = fields.Float(string="Bunga (%)", tracking=True)
    cicilan = fields.Integer(string="Jumlah Cicilan (Bulan)", tracking=True)

    periode_mulai = fields.Selection([
        ('januari', 'Januari'),
        ('februari', 'Februari'),
        ('maret', 'Maret'),
        ('april', 'April'),
        ('mei', 'Mei'),
        ('juni', 'Juni'),
        ('juli', 'Juli'),
        ('agustus', 'Agustus'),
        ('september', 'September'),
        ('oktober', 'Oktober'),
        ('november', 'November'),
        ('desember', 'Desember'),
    ], string="Periode Mulai", tracking=True)

    grace_period = fields.Integer(string="Grace Period (Bulan)", tracking=True)
    
    file_excel = fields.Binary('File Excel')
    file_name = fields.Char('Nama File Excel')
    angsuran_line_ids = fields.One2many('tagihan.rutin.line', 'tagihan_rutin_id', string="Detail Angsuran")


    # Fields Komputasi untuk Total
    total_sisa_pokok = fields.Float(string='Total Sisa Pokok', compute='_compute_totals', store=True)
    total_nominal_pokok = fields.Float(string='Total Nominal Pokok', compute='_compute_totals', store=True)
    total_nominal_bunga = fields.Float(string='Total Nominal Bunga', compute='_compute_totals', store=True)
    total_nominal_angsuran = fields.Float(string='Total Pengembalian', compute='_compute_totals', store=True)
    total_nominal_pembayaran = fields.Float(string='Total Nominal Pembayaran', compute='_compute_totals', store=True)

    total_nominal_dibayar = fields.Float(
        string="Total Sudah Dibayar", compute="_compute_totals", store=True
    )
    total_nominal_belum_dibayar = fields.Float(
        string="Total Belum Dibayar", compute="_compute_totals", store=True
    )

    shl_id = fields.Many2one(
        'account.keuangan.shl', 
        string='Shareholder Loan'
    )

    shl_option = fields.Selection([
        ('shl', 'SHL'),
        ('lainnya', 'Lainnya')
    ], string='Tipe', default='')

    lainnya = fields.Float('Lainnya')

    nominal_pinjaman = fields.Float(
        string='Nominal Pinjaman',
        compute='_compute_nominal_pinjaman',
        store=True
    )

    @api.depends('shl_id', 'shl_option', 'lainnya')
    def _compute_nominal_pinjaman(self):
        for record in self:
            if record.shl_option == 'shl' and record.shl_id:
                record.nominal_pinjaman = record.shl_id.nominal_perjanjian or 0.0
            elif record.shl_option == 'lainnya':
                record.nominal_pinjaman = record.lainnya or 0.0
            else:
                record.nominal_pinjaman = 0.0


    @api.depends('angsuran_line_ids.sisa_pokok', 
                 'angsuran_line_ids.nominal_pokok', 
                 'angsuran_line_ids.nominal_bunga', 
                 'angsuran_line_ids.nominal_pembayaran')

    def _compute_totals(self):
        for record in self:
            record.total_sisa_pokok = sum(line.sisa_pokok for line in record.angsuran_line_ids)
            record.total_nominal_pokok = sum(line.nominal_pokok for line in record.angsuran_line_ids)
            record.total_nominal_bunga = sum(line.nominal_bunga for line in record.angsuran_line_ids)
            record.total_nominal_angsuran = sum(line.nominal_cicilan for line in record.angsuran_line_ids)  # Asumsi Nominal Angsuran = Nominal Pembayaran
            record.total_nominal_pembayaran = sum(line.nominal_pembayaran for line in record.angsuran_line_ids)
            
            record.total_nominal_dibayar = sum(
                line.nominal_pembayaran for line in record.angsuran_line_ids
                if line.status_pembayaran in ('sudah_dibayar', 'lebih_bayar')
            )
            record.total_nominal_belum_dibayar = sum(
                line.nominal_pembayaran for line in record.angsuran_line_ids
                if line.status_pembayaran in ('belum_dibayar', 'kurang_bayar')
            )

    @api.onchange('nominal_pinjaman', 'bunga', 'cicilan', 'periode_mulai', 'grace_period')
    def _onchange_generate_angsuran(self):
        self.generate_angsuran()

    def generate_angsuran(self):
        """Mengenerate detail angsuran per bulan berdasarkan nominal, bunga, dan jumlah cicilan."""
        self.angsuran_line_ids = [(5, 0, 0)]  # Hapus angsuran yang ada
        
        if self.nominal_pinjaman > 0 and self.cicilan > 0:
            bunga_bulanan = self.bunga / 100 / 12  # Ubah menjadi bunga bulanan
            pokok_pinjaman = self.nominal_pinjaman
            jumlah_cicilan = self.cicilan

            # Menghitung jumlah angsuran bulanan menggunakan metode anuitas
            angsuran_bulanan = pokok_pinjaman * (bunga_bulanan / (1 - (1 + bunga_bulanan) ** -jumlah_cicilan))
            sisa_pokok = pokok_pinjaman

            # Menentukan bulan mulai berdasarkan periode_mulai dan grace_period
            periode_mulai_mapping = {
                'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 
                'juni': 6, 'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 
                'november': 11, 'desember': 12
            }

            # Cek apakah periode_mulai valid
            if not self.periode_mulai or self.periode_mulai not in periode_mulai_mapping:
                # Atur periode_mulai ke Januari jika kosong atau tidak valid
                self.periode_mulai = 'januari'

            bulan_mulai = periode_mulai_mapping[self.periode_mulai]
            bulan_angsuran = bulan_mulai + self.grace_period  # Angsuran dimulai setelah grace period

            # Pastikan bulan_angsuran berada dalam batas bulan 1 sampai 12
            if bulan_angsuran > 12:
                bulan_angsuran -= 12

            tanggal_mulai = datetime(datetime.now().year, bulan_angsuran, 1)

            for bulan in range(1, jumlah_cicilan + 1):
                # Menghitung nominal pokok dan nominal bunga untuk bulan ini
                nominal_bunga = round(bunga_bulanan * sisa_pokok)
                nominal_pokok = round(angsuran_bulanan - nominal_bunga)
                sisa_pokok -= nominal_pokok

                # Menghitung periode dan nominal pembayaran
                periode = (tanggal_mulai + relativedelta(months=bulan-1)).strftime("%B %Y")
                nominal_cicilan = nominal_pokok + nominal_bunga

                # Tambahkan detail angsuran ke dalam line
                self.angsuran_line_ids.create({
                    'tagihan_rutin_id': self.id,
                    'periode': periode,
                    'sisa_pokok': max(sisa_pokok, 0),  # Pastikan tidak negatif
                    'nominal_pokok': nominal_pokok,
                    'nominal_bunga': nominal_bunga,
                    'tgl_pembayaran': None,  # Diisi nanti saat pembayaran dilakukan
                    'nominal_cicilan': nominal_cicilan,
                    # 'status_pembayaran': 'belum'
                })


    def export_to_excel(self):
        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Detail Angsuran')

        # Menambahkan header
        headers = ['Periode', 'Nominal Pokok', 'Sisa Pokok', 'Nominal Bunga', 'Tanggal Pembayaran', 
                   'Nominal Angsuran', 'Nominal Pembayaran', 'Status Pembayaran']
        for col, header in enumerate(headers):
            sheet.write(0, col, header)

        # Isi data dari `angsuran_line_ids`
        row = 1
        for line in self.angsuran_line_ids:
            sheet.write(row, 0, line.periode)
            sheet.write(row, 1, line.nominal_pokok)
            sheet.write(row, 2, line.sisa_pokok)
            sheet.write(row, 3, line.nominal_bunga)
            sheet.write(row, 4, line.tgl_pembayaran.strftime('%Y-%m-%d') if line.tgl_pembayaran else '')
            sheet.write(row, 5, line.nominal_cicilan)
            sheet.write(row, 6, line.nominal_pembayaran)
            sheet.write(row, 7, line.status_pembayaran)
            row += 1

        # Selesaikan dan simpan file
        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Buat attachment dari file
        attachment = self.env['ir.attachment'].create({
            'name': f'Detail_Angsuran_{self.name}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'store_fname': f'Detail_Angsuran_{self.name}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'tagihan.rutin',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class TagihanRutinLine(models.Model):
    _name = 'tagihan.rutin.line'
    _description = 'Tagihan Rutin Line'

    tagihan_rutin_id = fields.Many2one('tagihan.rutin', string='Tagihan Rutin')
    periode = fields.Char(string='Periode (Bulan Tahun)')
    nominal_pokok = fields.Float(string='Nominal Pokok', compute='_compute_nominal_pokok', store=True)
    sisa_pokok = fields.Float(string='Sisa Pokok', compute='_compute_sisa_pokok', store=True)
    nominal_bunga = fields.Float(string='Nominal Bunga', compute='_compute_nominal_bunga', store=True)
    tgl_pembayaran = fields.Date(string='Tanggal Pembayaran')
    nominal_cicilan = fields.Float(string='Nominal Angsuran', compute='_compute_nominal_cicilan', store=True)
    nominal_bayar = fields.Float(string='Lebih / Kurang Bayar', compute='_compute_nominal_bayar', store=True)
    nominal_pembayaran = fields.Float(string='Nominal Pembayaran', store=True)
    status_pembayaran = fields.Selection([
        ('belum_dibayar', 'Belum Dibayar'),
        ('sudah_dibayar', 'Sudah Dibayar'),
        ('kurang_bayar', 'Kurang Bayar'),
        ('lebih_bayar', 'Lebih Bayar'),
    ], string='Status Pembayaran', default='belum_dibayar', compute='_compute_status_pembayaran', store=True)
    sisa_cicilan = fields.Float(string='Sisa Angsuran', compute='_compute_sisa_cicilan', store=True)
    sisa_cicilan_next = fields.Float(string='Sisa Cicilan Sebelumnya', compute='_compute_sisa_cicilan_next', store=True)

    keterangan = fields.Char(string='Keterangan')


    @api.depends('tagihan_rutin_id.nominal_pinjaman', 'tagihan_rutin_id.cicilan')
    def _compute_nominal_pokok(self):
        for line in self:
            if line.tagihan_rutin_id.nominal_pinjaman and line.tagihan_rutin_id.cicilan:
                line.nominal_pokok = round(line.tagihan_rutin_id.nominal_pinjaman / line.tagihan_rutin_id.cicilan, 0)

    @api.depends('nominal_pokok', 'status_pembayaran', 'tagihan_rutin_id.cicilan', 'tagihan_rutin_id.nominal_pinjaman')
    def _compute_sisa_pokok(self):
        for line in self:
            if line.status_pembayaran == 'belum_dibayar':
                first_line = self.search([('tagihan_rutin_id', '=', line.tagihan_rutin_id.id)], order='id', limit=1)
                if first_line:
                    if line == first_line:
                        line.sisa_pokok = round(line.tagihan_rutin_id.nominal_pinjaman, 0)
                    else:
                        previous_line = self.search([
                            ('tagihan_rutin_id', '=', line.tagihan_rutin_id.id),
                            ('id', '<', line.id)
                        ], order='id desc', limit=1)
                        if previous_line:
                            line.sisa_pokok = round(previous_line.sisa_pokok - previous_line.nominal_pokok, 0)
                else:
                    line.sisa_pokok = round(line.tagihan_rutin_id.nominal_pinjaman, 0)
            else:
                line.sisa_pokok = line.sisa_pokok


    @api.depends('sisa_pokok', 'tagihan_rutin_id.bunga')
    def _compute_nominal_bunga(self):
        for line in self:
            if line.sisa_pokok and line.tagihan_rutin_id.bunga:
                line.nominal_bunga = round(((line.sisa_pokok * line.tagihan_rutin_id.bunga) / 100) / 12, 0)

    @api.depends('nominal_pokok', 'nominal_bunga', 'sisa_cicilan_next')
    def _compute_nominal_cicilan(self):
        for line in self:
            line.nominal_cicilan = round((line.nominal_pokok + line.nominal_bunga) + -line.sisa_cicilan_next, 0)
    

    # @api.onchange('nominal_pokok', 'nominal_bunga', 'tagihan_rutin_id')
    # def _compute_nominal_cicilan(self):
    #     for line in self:
    #         base = round(line.nominal_pokok + line.nominal_bunga, 0)
    #         tambahan = 0
    #         if isinstance(line.id, int):
    #             previous_line = self.search([
    #                 ('tagihan_rutin_id', '=', line.tagihan_rutin_id.id),
    #                 ('id', '<', line.id)
    #             ], order='id desc', limit=1)
    #             if previous_line:
    #                 tambahan = previous_line.sisa_cicilan  # bisa negatif (kurang) atau positif (lebih)
    #         line.nominal_cicilan = base + tambahan

    @api.depends('nominal_cicilan', 'nominal_pembayaran')
    def _compute_nominal_bayar(self):
        for line in self:
            # Hitung selisih antara nominal_pembayaran dan nominal_cicilan
            # Hasilkan selisih sebagai negatif jika kurang bayar, positif jika lebih bayar
            line.nominal_bayar = line.nominal_pembayaran - line.nominal_cicilan

    @api.depends('nominal_cicilan', 'nominal_pembayaran')
    def _compute_sisa_cicilan(self):
        for line in self:
            # Jika nominal_pembayaran masih 0, set sisa_cicilan ke 0
            if line.nominal_pembayaran == 0:
                line.sisa_cicilan = 0
            else:
                # Hitung selisih antara nominal_pembayaran dan nominal_cicilan
                # Hasilkan selisih sebagai negatif jika kurang bayar, positif jika lebih bayar
                line.sisa_cicilan = line.nominal_cicilan - line.nominal_pembayaran

    @api.depends('nominal_bayar', 'nominal_pembayaran', 'nominal_cicilan')
    def _compute_status_pembayaran(self):
        for line in self:
            if not line.nominal_pembayaran:  # Jika nominal pembayaran kosong
                line.status_pembayaran = 'belum_dibayar'
            elif line.nominal_bayar == 0:  # Jika nominal bayar sama dengan 0
                line.status_pembayaran = 'sudah_dibayar'
            elif line.nominal_bayar < 0:  # Jika nominal bayar negatif (kurang bayar)
                line.status_pembayaran = 'kurang_bayar'
            elif line.nominal_bayar > 0:  # Jika nominal bayar positif (lebih bayar)
                line.status_pembayaran = 'lebih_bayar'
                

    @api.depends('nominal_cicilan', 'nominal_pembayaran')
    def _compute_sisa_cicilan_next(self):
        for line in self:
            # Cari baris berikutnya dengan tagihan_rutin_id yang sama dan id yang lebih besar
            if line.id:
                next_line = self.search([
                    ('tagihan_rutin_id', '=', line.tagihan_rutin_id.id),
                    ('id', '>', line.id)  # Pastikan urutan berdasarkan id untuk mencari baris berikutnya
                ], order='id asc', limit=1)

                if next_line:
                    # Jika ada baris berikutnya, set nilai sisa cicilan pada baris berikutnya
                    next_line.sisa_cicilan_next = -line.sisa_cicilan


