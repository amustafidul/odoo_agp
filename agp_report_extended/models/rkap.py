from odoo import models, fields, api

class RKAP(models.Model):
    _inherit = 'account.keuangan.rkap'

    def _get_next_year(self):
        if self.tahun_anggaran:
            return str(int(self.tahun_anggaran) + 1)
        return None

    def _get_prev_year(self):
        if self.tahun_anggaran:
            return str(int(self.tahun_anggaran) - 1)
        return None

    tahun_anggaran_next = fields.Char(string="Tahun Anggaran Next", compute='_compute_tahun_anggaran_next')
    tahun_anggaran_prev = fields.Char(string="Tahun Anggaran Previous", compute='_compute_tahun_anggaran_prev')
    # kegiatan_ids = fields.Many2many(comodel_name='jenis.kegiatan', string='Kegiatan IDs', compute='_compute_kegiatan_ids')
    kegiatan_line_ids = fields.One2many('jenis.kegiatan.rkap.line', 'rkap_id', string='Kegiatan IDs')
    jumlah_beban = fields.Float(string='Jumlah Beban', compute='_compute_jumlah_beban', store=True)
    pemakaian_beban = fields.Float(string='Pemakaian Beban', compute='_compute_pemakaian_beban', store=True)
    tahun_anggaran_int = fields.Integer(string='Tahun Anggaran Int', compute='_compute_tahun_anggaran_int', store=True)
    sum_ri_thdp_rkap_income = fields.Float(string='Sum RI THDP RKAP Income', compute='_compute_sum_ri_thdp_rkap_income', store=True)
    sum_ri_thdp_rkap_income_prev = fields.Float(string='Sum RI THDP RKAP Income Prev', compute='_compute_sum_ri_thdp_rkap_income_prev', store=True)
    sum_ri_thdp_rkap_expense = fields.Float(string='Sum RI THDP RKAP Expenses', compute='_compute_sum_ri_thdp_rkap_expense', store=True)
    sum_ri_thdp_rkap_expense_prev = fields.Float(string='Sum RI THDP RKAP Expenses Prev', compute='_compute_sum_ri_thdp_rkap_expense_prev', store=True)
    sum_ri_thdp_rkap_expense_gen = fields.Float(string='Sum RI THDP RKAP Expenses', compute='_compute_sum_ri_thdp_rkap_expense_gen', store=True)
    sum_ri_thdp_rkap_expense_gen_prev = fields.Float(string='Sum RI THDP RKAP Expenses Prev', compute='_compute_sum_ri_thdp_rkap_expense_gen_prev', store=True)

    # konsolidasi_line_ids = fields.One2many('account.keuangan.rkap.konsolidasi', 'rkap_id', string='List Konsolidasi')
    # res_query_konsolidasi = fields.Char(string='Hasil Query Konsolidasi', compute='_compute_res_query_konsolidasi', store=True)

    def action_generate_konsolidasi(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate RKAP Konsolidasi',
            'res_model': 'rkap.konsolidasi.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.depends('rkap_line_ids.ri_terhadap_rkap', 'rkap_line_ids.kode_anggaran_id.kode_anggaran')
    def _compute_sum_ri_thdp_rkap_expense_gen(self):
        for record in self:
            sum_ri = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('6'):
                    sum_ri += line.ri_terhadap_rkap
            record.sum_ri_thdp_rkap_expense_gen = sum_ri

    @api.depends('rkap_line_ids.ri_terhadap_rkap_prev', 'rkap_line_ids.kode_anggaran_id.kode_anggaran')
    def _compute_sum_ri_thdp_rkap_expense_gen_prev(self):
        for record in self:
            sum_ri_prev = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('6'):
                    sum_ri_prev += line.ri_terhadap_rkap_prev
            record.sum_ri_thdp_rkap_expense_gen_prev = sum_ri_prev

    @api.depends('rkap_line_ids.ri_terhadap_rkap', 'rkap_line_ids.kode_anggaran_id.kode_anggaran')
    def _compute_sum_ri_thdp_rkap_expense(self):
        for record in self:
            sum_ri = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('5'):
                    sum_ri += line.ri_terhadap_rkap
            record.sum_ri_thdp_rkap_expense = sum_ri

    @api.depends('rkap_line_ids.ri_terhadap_rkap_prev', 'rkap_line_ids.kode_anggaran_id.kode_anggaran')
    def _compute_sum_ri_thdp_rkap_expense_prev(self):
        for record in self:
            sum_ri_prev = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('5'):
                    sum_ri_prev += line.ri_terhadap_rkap_prev
            record.sum_ri_thdp_rkap_expense_prev = sum_ri_prev

    # @api.depends('rkap_line_ids.ri_terhadap_rkap', 'rkap_line_ids.kode_anggaran_id.kode_anggaran')
    # def _compute_sum_ri_thdp_rkap_income(self):
    #     for record in self:
    #         sum_ri = 0.0
    #         for line in record.rkap_line_ids:
    #             if line.kode_anggaran_id.kode_anggaran.startswith('4'):
    #                 sum_ri += line.ri_terhadap_rkap
    #         record.sum_ri_thdp_rkap_income = sum_ri

    @api.depends('pemakaian_pemasukan', 'jumlah_pemasukan')
    def _compute_sum_ri_thdp_rkap_income(self):
        for record in self:
            if record.jumlah_pemasukan != 0:
                record.sum_ri_thdp_rkap_income = record.pemakaian_pemasukan / record.jumlah_pemasukan
            else:
                record.sum_ri_thdp_rkap_income = 0.0

    @api.depends('rkap_line_ids.ri_terhadap_rkap_prev', 'rkap_line_ids.kode_anggaran_id.kode_anggaran')
    def _compute_sum_ri_thdp_rkap_income_prev(self):
        for record in self:
            sum_ri_prev = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('4'):
                    sum_ri_prev += line.ri_terhadap_rkap_prev
            record.sum_ri_thdp_rkap_income_prev = sum_ri_prev

    @api.depends('tahun_anggaran')
    def _compute_tahun_anggaran_int(self):
        for record in self:
            try:
                record.tahun_anggaran_int = int(record.tahun_anggaran) if record.tahun_anggaran else 0
            except ValueError:
                record.tahun_anggaran_int = 0

    @api.depends('rkap_line_ids.kode_anggaran_id', 'rkap_line_ids.nominal')
    def _compute_jumlah_beban(self):
        for record in self:
            jumlah_beban = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('5'):
                    jumlah_beban += line.nominal
            record.jumlah_beban = jumlah_beban

    @api.depends('rkap_line_ids.kode_anggaran_id', 'rkap_line_ids.pemakaian_anggaran')
    def _compute_pemakaian_beban(self):
        for record in self:
            pemakaian_beban = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.kode_anggaran.startswith('5'):
                    pemakaian_beban += line.pemakaian_anggaran
            record.pemakaian_beban = pemakaian_beban

    # def _compute_kegiatan_ids(self):
    #     for record in self:
    #         kegiatans = self.env['jenis.kegiatan'].sudo().search([])
    #         record.kegiatan_ids = [(6, 0, kegiatans.ids)]

    @api.depends('tahun_anggaran')
    def _compute_tahun_anggaran_next(self):
        for rec in self:
            rec.tahun_anggaran_next = self._get_next_year()

    @api.depends('tahun_anggaran')
    def _compute_tahun_anggaran_prev(self):
        for rec in self:
            rec.tahun_anggaran_prev = self._get_prev_year()

class RKAPLines(models.Model):
    _inherit = 'account.keuangan.rkap.line'

    rkap_next = fields.Float(string='Nilai RKAP Tahun Depan')
    nominal_prev = fields.Float(string='Nilai RKAP Tahun Sebelumnya', compute='_compute_nilai_nominal_prev')
    nominal_next = fields.Float(string='Nilai RKAP Tahun Selanjutnya')
    ri_terhadap_rkap = fields.Float(string='Realisasi Tahunan', compute='_compute_ri_terhadap_rkap', store=True)
    ri_terhadap_rkap_next = fields.Float(string='Realisasi Tahun Depan', compute='_compute_ri_terhadap_rkap_next', store=True)
    ri_terhadap_rkap_prev = fields.Float(string='Realisasi Tahun Sebelumnya', compute='_compute_ri_terhadap_rkap_prev', store=True)
    unique_account_code = fields.Char(string="Unique Account Code", compute='_compute_unique_account_code', store=False)
    nominal_by_prefix = fields.Float(string='Nominal by Prefix', compute='_compute_nominal_by_prefix', store=True)
    nominal_by_prefix_six = fields.Float(string='Nominal by Prefix Six', compute='_compute_nominal_by_prefix_six', store=True)
    tahun_anggaran_int = fields.Integer(string='Tahun Int', related='rkap_id.tahun_anggaran_int', store=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Cabang', related='rkap_id.branch_id')
    pemakaian_anggaran_by_prefix = fields.Float(string='Pemakaian Anggaran by Prefix', compute='_compute_pemakaian_anggaran_by_prefix', store=True)
    nominal_next_by_prefix = fields.Float(string='RKAP Next by Prefix', compute='_compute_nominal_next_by_prefix', store=True)
    ri_terhadap_rkap_prefix_51 = fields.Float('Realisasi Tahunan 51', compute='_compute_ri_terhadap_rkap_prefix_expenses', store=True)
    ri_terhadap_rkap_prefix_61 = fields.Float('Realisasi Tahunan 61', compute='_compute_ri_terhadap_rkap_prefix_expenses', store=True)
    # ri_terhadap_rkap_prefix_61 = fields.Float('Realisasi Tahunan 51', compute='_compute_ri_terhadap_rkap_prefix_51', store=True)

    @api.depends('ri_terhadap_rkap', 'kode_anggaran_id.kode_anggaran')
    def _compute_ri_terhadap_rkap_prefix_expenses(self):
        for line in self:
            if line.kode_anggaran_id and line.kode_anggaran_id.kode_anggaran.startswith('51'):
                total = sum(
                    l.ri_terhadap_rkap
                    for l in self.search([('kode_anggaran_id.kode_anggaran', 'like', '51%')])
                )
                line.ri_terhadap_rkap_prefix_51 = total
            elif line.kode_anggaran_id and line.kode_anggaran_id.kode_anggaran.startswith('61'):
                total = sum(
                    l.ri_terhadap_rkap
                    for l in self.search([('kode_anggaran_id.kode_anggaran', 'like', '61%')])
                )
                line.ri_terhadap_rkap_prefix_61 = total

    @api.depends('nominal', 'nominal_prev')
    def _compute_ri_terhadap_rkap_prev(self):
        for line in self:
            if line.nominal and line.nominal_prev:
                # raw_result = line.nominal / line.nominal_prev - 1
                raw_result = line.nominal / line.nominal_prev
                if raw_result < 1:
                    line.ri_terhadap_rkap_prev = raw_result * 100
                elif 1 <= raw_result <= 100.0:
                    line.ri_terhadap_rkap_prev = raw_result
            else:
                line.ri_terhadap_rkap_prev = 0.0

    @api.depends('nominal', 'nominal_next')
    def _compute_ri_terhadap_rkap_next(self):
        for line in self:
            if line.nominal and line.nominal_next:
                # raw_result = line.nominal_next / line.nominal - 1
                raw_result = line.nominal_next / line.nominal
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

    @api.depends('kode_anggaran_id.kode_anggaran', 'nominal')
    def _compute_nominal_by_prefix_six(self):
        for line in self:
            prefix = line.kode_anggaran_id.kode_anggaran[:2] if line.kode_anggaran_id else ''
            if prefix.isdigit() and 61 <= int(prefix) <= 69:
                line.nominal_by_prefix_six = line.nominal
            else:
                line.nominal_by_prefix_six = 0.0

    @api.depends('kode_anggaran_id.kode_anggaran', 'pemakaian_anggaran')
    def _compute_pemakaian_anggaran_by_prefix(self):
        for line in self:
            prefix = line.kode_anggaran_id.kode_anggaran[:2] if line.kode_anggaran_id else ''
            if prefix.isdigit() and 51 <= int(prefix) <= 59:
                line.pemakaian_anggaran_by_prefix = line.pemakaian_anggaran
            else:
                line.pemakaian_anggaran_by_prefix = 0.0

    @api.depends('kode_anggaran_id.kode_anggaran', 'nominal_next')
    def _compute_nominal_next_by_prefix(self):
        for line in self:
            prefix = line.kode_anggaran_id.kode_anggaran[:2] if line.kode_anggaran_id else ''
            if prefix.isdigit() and 51 <= int(prefix) <= 59:
                line.nominal_next_by_prefix = line.nominal_next
            else:
                line.nominal_next_by_prefix = 0.0

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
                # raw_result = rec.pemakaian_anggaran / rec.nominal - 1
                raw_result = rec.pemakaian_anggaran / rec.nominal
                if raw_result < 1:
                    rec.ri_terhadap_rkap = raw_result * 100
                elif 1 <= raw_result <= 100.0:
                    rec.ri_terhadap_rkap = raw_result
            else:
                rec.ri_terhadap_rkap = 0.0

                # dec_ri = rec.pemakaian_anggaran / rec.nominal
                # dec_ri_div = dec_ri * 100
                # rec.ri_terhadap_rkap = round(dec_ri_div, 2)

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
