from odoo import models, fields, api

class JenisKegiatan(models.Model):
    _name = 'jenis.kegiatan.rkap.line'

    kegiatan_id = fields.Many2one('jenis.kegiatan', string='Nama Kegiatan')
    company_id = fields.Many2one('res.company', string='Company')
    rkap_id = fields.Many2one('account.keuangan.rkap', string='RKAP')
    rkap_next = fields.Float(string='Nilai RKAP Tahun Depan')
    nominal_prev = fields.Float(string='Nilai RKAP Tahun Sebelumnya', compute='_compute_nilai_nominal_prev')
    nominal_next = fields.Float(string='Nilai RKAP Tahun Selanjutnya')
    ri_terhadap_rkap = fields.Float(string='Realisasi Tahunan', compute='_compute_ri_terhadap_rkap', store=True)
    ri_terhadap_rkap_next = fields.Float(string='Realisasi Tahun Selanjutnya', compute='_compute_ri_terhadap_rkap_next', store=True)
    ri_terhadap_rkap_prev = fields.Float(string='Realisasi Tahun Sebelumnya', compute='_compute_ri_terhadap_rkap_prev', store=True)
    unique_account_code = fields.Char(string="Unique Account Code", compute='_compute_unique_account_code', store=False)
    nominal_by_prefix = fields.Float(string='Nominal by Prefix', compute='_compute_nominal_by_prefix', store=True)
    tahun_anggaran_int = fields.Integer(string='Tahun Int', related='rkap_id.tahun_anggaran_int', store=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Cabang', related='rkap_id.branch_id')
    nominal = fields.Float(string='Nominal Anggaran', required=True, tracking=True)
    kode_anggaran_id = fields.Many2one(
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran',
        required=True,
        ondelete='cascade'
    )
    account_code_id = fields.Many2one('account.account', string='Account Code', readonly=False, tracking=True)
    pemakaian_anggaran = fields.Float(string='Realisasi Anggaran', compute='_compute_pemakaian_anggaran', store=True, tracking=True)
    realisasi = fields.Float(string='Sisa Anggaran', compute='_compute_realisasi', store=True, tracking=True)
    deskripsi = fields.Text(string='Deskripsi Anggaran', readonly=False, tracking=True)

    @api.depends('kode_anggaran_id', 'branch_id')
    def _compute_realisasi(self):
        for record in self:
            # Search for the saldo record that matches both kode_anggaran_id and branch_id
            saldo_record = self.env['account.keuangan.saldo'].search([
                ('kode_anggaran_id', '=', record.kode_anggaran_id.id),
                ('branch_id', '=', record.branch_id.id)
            ], limit=1)
            # Set the pagu_limit based on the saldo found, default to 0 if not found
            record.realisasi = saldo_record.saldo if saldo_record else 0.0

    @api.depends('nominal', 'realisasi')
    def _compute_pemakaian_anggaran(self):
        for record in self:
            record.pemakaian_anggaran = record.nominal - record.realisasi

    @api.depends('nominal', 'nominal_prev')
    def _compute_ri_terhadap_rkap_prev(self):
        for line in self:
            if line.nominal and line.nominal_prev:
                raw_result = line.nominal / line.nominal_prev - 1
                if raw_result < 1:
                    line.ri_terhadap_rkap_prev = raw_result * 100
                elif 1 <= raw_result <= 100.0:
                    line.ri_terhadap_rkap_prev = raw_result
            else:
                line.ri_terhadap_rkap_prev = 0.0

    @api.depends('nominal', 'nominal_next')
    def _compute_ri_terhadap_rkap_next(self):
        for line in self:
            if line.nominal and line.nominal_next != 0.0:
                raw_result = line.nominal_next / line.nominal - 1
                if raw_result < 1:
                    line.ri_terhadap_rkap_next = raw_result * 100
                elif 1 <= raw_result <= 100.0:
                    line.ri_terhadap_rkap_next = raw_result
            else:
                line.ri_terhadap_rkap_next = 0.0

    @api.depends('kode_anggaran_id.kode_anggaran', 'nominal')
    def _compute_nominal_by_prefix(self):
        for line in self:
            prefix = line.kode_anggaran_id.kode_anggaran[:2] if line.kode_anggaran_id else ''
            if prefix.isdigit() and 51 <= int(prefix) <= 59:
                line.nominal_by_prefix = line.nominal
            else:
                line.nominal_by_prefix = 0.0

    @api.depends('account_code_id', 'kode_anggaran_id')
    def _compute_unique_account_code(self):
        processed_kode_anggaran = set()

        for line in self:
            kode_anggaran_id = line.kode_anggaran_id
            kode_anggaran_code = kode_anggaran_id.kode_anggaran if kode_anggaran_id else None
            account_code = line.account_code_id.code if line.account_code_id else None

            if kode_anggaran_id:
                if kode_anggaran_code in processed_kode_anggaran:
                    line.unique_account_code = 'null'
                else:
                    line.unique_account_code = account_code
                    processed_kode_anggaran.add(kode_anggaran_code)
            else:
                line.unique_account_code = 'null'

    @api.depends('nominal', 'pemakaian_anggaran')
    def _compute_ri_terhadap_rkap(self):
        for rec in self:
            if rec.nominal and rec.pemakaian_anggaran:
                raw_result = rec.nominal / rec.pemakaian_anggaran - 1
                if raw_result < 1:
                    rec.ri_terhadap_rkap = raw_result * 100
                elif 1 <= raw_result <= 100.0:
                    rec.ri_terhadap_rkap = raw_result
            else:
                rec.ri_terhadap_rkap = 0.0

    @api.depends(
        'rkap_id.tahun_anggaran_int',
        'account_code_id',
        'kode_anggaran_id',
        'deskripsi',
        'rkap_id.branch_id'
    )
    def _compute_nilai_nominal_prev(self):
        for line in self:
            line.nominal_prev = 0.0

            if not line.rkap_id or not line.rkap_id.tahun_anggaran:
                continue

            previous_lines = self.search([
                ('account_code_id', '=', line.account_code_id.id),
                ('kode_anggaran_id', '=', line.kode_anggaran_id.id),
                ('deskripsi', '=', line.deskripsi),
                ('tahun_anggaran_int', '<', line.tahun_anggaran_int),
                ('branch_id', '=', line.branch_id.id)
            ], limit=1)

            if previous_lines:
                closest_line = previous_lines.sorted(lambda l: l.rkap_id.tahun_anggaran, reverse=True)[0]
                line.nominal_prev = closest_line.realisasi
            else:
                line.nominal_prev = line.nominal_prev
