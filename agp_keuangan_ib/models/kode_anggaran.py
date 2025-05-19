from odoo import models, fields, api, _

class KodeAnggaran(models.Model):
    _name = 'account.keuangan.kode.anggaran'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Kode Anggaran'
    _rec_name = 'kode_anggaran'

    kode_anggaran = fields.Char(string='Kode Anggaran', 
                                size=64, 
                                required=True, 
                                tracking=True, 
                                unaccent=False, 
                                ondelete='cascade')

    account_type = fields.Selection(
        selection=[
            ("masuk", "Pemasukan"),
            ("keluar", "Pengeluaran"),
        ],
        string="Type", tracking=True,
        required=True,
        store=True, readonly=False, precompute=True, index=True,
        help="Account Type is used for information purpose, to generate country-specific legal reports, and set the rules to close a fiscal year and generate opening entries."
    )
    deskripsi = fields.Text(string='Deskripsi', required=True)

    # Field Many2one untuk memilih akun dari account.account, hanya kode yang ditampilkan
    account_code_id = fields.Many2one(
        'account.account',
        string='Account Code',
        domain="[('code', '!=', False)]",  # Hanya tampilkan akun yang memiliki kode
        required=True
    )

    unit_penempatan_id = fields.Many2one('hr.employee.unit', string='Divisi')

    kelompok = fields.Selection(
        selection=[
            ("penerimaan_emkl", "PENERIMAAN EMKL (PIUTANG)"),
            ("penerimaan_bongkar_muat", "PENERIMAAN BONGKAR MUAT (PIUTANG)"),
            ("penerimaan_keagenan", "PENERIMAAN KEAGENAN (PIUTANG)"),
            ("penerimaan_tug_assist", "PENERIMAAN TUG ASSIST (PIUTANG)"),
            ("penerimaan_jetty_management", "PENERIMAAN JETTY MANAJEMEN (PIUTANG)"),
            ("penerimaan_uang_muka_lainnya", "PENERIMAAN OPERASI LAINNYA"),
            ("penerimaan_logistik", "PENERIMAAN LOGISTIK"),
            # ("biaya_administrasi_umum", "BIAYA ADMINISTRASI DAN UMUM"),
            # ("biaya_ops_jetty_pmb", "BIAYA OPERASIONAL JETTY & PBM"),
            ("anggaran_emkl", "ANGGARAN EMKL"),
            ("anggaran_bongkar_muat", "ANGGARAN BONGKAR MUAT"),
            ("anggaran_keagenan", "ANGGARAN KEAGENAN"),
            ("anggaran_tug_assist", "ANGGARAN TUG ASSIST"),
            ("anggaran_jetty", "ANGGARAN JETTY MANAJEMEN"),
            ("anggaran_lainnya", "ANGGARAN OPERASI LAINNYA"),
            ("anggaran_logistik", "ANGGARAN LOGISTIK"),
            ("anggaran_gaji", "ANGGARAN GAJI, TUNJANGAN DAN HONORARIUM"),
            ("anggaran_pemeliharaan", "ANGGARAN PEMELIHARAAN DAN PERBAIKAN"),
            ("anggaran_perlengkapan", "ANGGARAN PERLENGKAPAN KANTOR DAN SISTEM INFORMASI"),
            ("anggaran_utilitas", "ANGGARAN RT KANTOR, UTILITAS, POS DAN TELEKOMUNIKASI"),
            ("anggaran_sewa_asuransi", "ANGGARAN SEWA DAN ASURANSI"),
            ("anggaran_penyusutan", "ANGGARAN PENYUSUTAN, PENYISIHAN DAN AMORTISASI"),
            ("anggaran_adm", "ANGGARAN ADMINISTRASI DAN UMUM LAINNYA"),
            ("peg_tetap", "PEGAWAI TETAP"),
            ("peg_kontrak_kerja", "PEGAWAI KONTRAK KERJA"),
            ("dir_komisaris", "DIREKSI DAN KOMISARIS"),
            ("pemeliharaan_perbaikan", "PEMELIHARAAN DAN PERBAIKAN"),
            ("perlengkapan_kantor_sistem", "PERLENGKAPAN KANTOR DAN SISTEM INFORMASI"),
            ("kantor_utilitas_pos", "RT KANTOR, UTILITAS, POS DAN TELEKOMUNIKASI"),
            ("sewa_asuransi", "SEWA DAN ASURANSI"),
            ("penyusutan_penyisihan", "PENYUSUTAN, PENYISIHAN DAN AMORTISASI"),
            ("adm_lainnya", "ADMINISTRASI DAN UMUM LAINNYA"),
            ("pendapatan_luar_operasi", "PENDAPATAN DILUAR OPERASI"),
            ("beban_luar_operasi", "BEBAN DILUAR OPERASI")

        ],
        string="Kelompok", tracking=True,
        required=True,
        store=True, readonly=False, precompute=True, index=True
    )

    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan', tracking=True)

    saldo = fields.Float(string='Saldo', compute='_compute_saldo', store=True)
    rkap_line_ids = fields.One2many('account.keuangan.rkap.line', 'kode_anggaran_id', string='RKAP Lines')


    @api.depends('rkap_line_ids.nominal')
    def _compute_saldo(self):
        for record in self:
            record.saldo = sum(line.nominal for line in record.rkap_line_ids)

    def _reduce_saldo(self, amount):
        if self.saldo < amount:
            raise ValidationError(_('Saldo tidak mencukupi untuk mengurangi nilai ini!'))
        self.saldo -= amount

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.kode_anggaran))  # Menampilkan kode_anggaran sebagai nama
        return result