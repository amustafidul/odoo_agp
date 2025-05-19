from odoo import models, fields, api
from odoo.exceptions import ValidationError
from collections import defaultdict

import logging
_logger = logging.getLogger(__name__)


class AccountMonitorKKHCLine(models.Model):
    _name = 'account.keuangan.monitor.kkhc.line'
    _description = 'Monitoring KKHC Lines'

    kkhc_line_id = fields.Many2one('account.keuangan.kkhc.line', string='Item KKHC')
    # kkhc_kkhc_id = fields.Many2one('account.keuangan.kkhc', string='No. KKHC', store=True)
    kkhc_id = fields.Many2one('account.keuangan.kkhc', string='No. KKHC', related='kkhc_line_id.kkhc_id', store=True)
    nodin_id = fields.Many2one('account.keuangan.nota.dinas', string='No. Nodin', domain=[('state', '!=', 'approved')])
    nodin_bod_id = fields.Many2one('account.keuangan.nota.dinas.bod', string='No. Nodin BoD', domain=[('state', '!=', 'approved')])
    branch_id = fields.Many2one('res.branch', string='Cabang', related='kkhc_line_id.kkhc_id.branch_id', store=True)
    kode_anggaran_id = fields.Many2one(
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran',
        related='kkhc_line_id.kode_anggaran_id',
        store=True
    )
    deskripsi = fields.Text(string='Deskripsi Penggunaan', related='kkhc_line_id.deskripsi')
    account_code_id = fields.Many2one(
        'account.account',
        string='COA',
        related='kkhc_line_id.account_code_id',
        store=True
    )
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'IDR')], limit=1))
    nominal_pengajuan = fields.Float(string='Nominal Pengajuan', related='kkhc_line_id.nominal_pengajuan', store=True, tracking=True)
    nominal_disetujui = fields.Float(string='Nominal Disetujui', related='kkhc_line_id.nominal_disetujui', store=True, tracking=True)
    pagu_limit = fields.Float(string='Limit KKHC', related='kkhc_line_id.pagu_limit', store=True, tracking=True)
    sisa_pengajuan = fields.Float(string='Sisa Pengajuan', related='kkhc_line_id.sisa_pengajuan', store=True, tracking=True)
    # nominal_bayar_pertama = fields.Float(string='Bayar Termin 1', store=True, tracking=True) 
    tgl_bayar_pertama = fields.Date(string='Tgl Bayar Termin 1', store=True, tracking=True)
    nominal_bayar_kedua = fields.Float(string='Bayar Termin 2', store=True, tracking=True)
    tgl_bayar_kedua = fields.Date(string='Tgl Bayar Termin 2', store=True, tracking=True)
    type = fields.Selection([('usaha', 'KKHC Usaha'), ('umum', 'KKHC Umum')], string='Tipe KKHC', compute='_compute_type', store=True, tracking=True)
    nodin_id = fields.Many2one('account.keuangan.nota.dinas', string='No. Nodin')
    uraian = fields.Text(string='Uraian Penggunaan', related='kkhc_line_id.deskripsi_penggunaan')
    jumlah_biaya = fields.Float(string='Jumlah Biaya', store=True, tracking=True, default=0.0)
    active = fields.Boolean(string='Active', default=True, store=True)
    periode_kkhc_start = fields.Date(string='Awal Periode', related='kkhc_id.periode_kkhc_start', store=True)
    periode_kkhc_end = fields.Date(string='Akhir Periode', related='kkhc_id.periode_kkhc_end', store=True)
    kkhc_state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status KKHC', related='kkhc_id.state', store=True)
    sifat_kkhc = fields.Selection([
        ('prioritas', 'Prioritas'),
        ('non_prioritas', 'Non Prioritas')
    ], string='Sifat')
    header_state_non_bod = fields.Selection(string='Nodin State', related='nodin_id.state', readonly=True)
    header_state_bod = fields.Selection(string='Nodin BoD State', related='nodin_bod_id.state', readonly=True)
    is_dibayar = fields.Boolean(string='Dibayar')
    nominal_disetujui_usaha = fields.Float(string='Usaha/Umum')
    nominal_disetujui_anggaran = fields.Float(string='Anggaran', compute='_compute_nominal_disetujui_anggaran_default', readonly=False, store=True)
    nominal_disetujui_keuangan = fields.Float(string='Keuangan')
    nominal_bayar_pertama = fields.Float(string='Keuangan (Bayar 1)', compute='_compute_nominal_disetujui_keuangan_default', readonly=False, store=True)
    nominal_final = fields.Float(string='Final')
    is_locked_usaha = fields.Boolean("Locked by Usaha", default=False)
    is_locked_anggaran = fields.Boolean("Locked by Anggaran", default=False)
    is_locked_keuangan = fields.Boolean("Locked by Keuangan", default=False)

    # for pivot bu ade
    nominal_disetujui_operasional = fields.Float(string="Operasional", compute="_compute_nominal_disetujui", store=True)
    nominal_disetujui_umum = fields.Float(string="Umum", compute="_compute_nominal_disetujui", store=True)
    nominal_disetujui_total = fields.Float(string="Jumlah", compute="_compute_nominal_disetujui", store=True)

    # for printout nodin
    is_rejected = fields.Boolean(string='Rejected', default=False, store=True)
    total_per_cabang = fields.Float(compute='_compute_total_per_cabang', string='Total Nominal Per Cabang', store=True)
    user_level = fields.Char(compute='_compute_user_level')

    # New constraint
    _sql_constraints = [
        (
            'unique_monitoring_entry',
            'unique(kkhc_line_id, kode_anggaran_id, account_code_id)',
            'Satu baris KKHC hanya boleh punya satu monitoring dengan kombinasi Kode Anggaran & COA yang sama.'
        )
    ]

    def _compute_user_level(self):
        for record in self:
            record.user_level = self.env.user.level

    @api.depends('branch_id', 'nominal_final')
    def _compute_total_per_cabang(self):
        if not self:
            return

        self.env.cr.execute("""
            SELECT
                branch_id, SUM(nominal_final) 
            FROM
                account_keuangan_monitor_kkhc_line
            WHERE
                branch_id IS NOT NULL
            AND type = 'usaha'
            AND nodin_id IS NOT NULL
            AND kkhc_state = 'approved'
            AND is_rejected IS NOT TRUE
            GROUP BY branch_id, kkhc_id
        """)
        totals = dict(self.env.cr.fetchall())

        for record in self:
            record.total_per_cabang = totals.get(record.branch_id.id, 0.0)

    @api.depends('nominal_disetujui_usaha')
    def _compute_nominal_disetujui_anggaran_default(self):
        for rec in self:
            if not rec.nominal_disetujui_anggaran or rec.nominal_disetujui_anggaran == 0.0:
                rec.nominal_disetujui_anggaran = rec.nominal_disetujui_usaha

    @api.depends('nominal_disetujui_anggaran')
    def _compute_nominal_disetujui_keuangan_default(self):
        for rec in self:
            if not rec.nominal_bayar_pertama or rec.nominal_bayar_pertama == 0.0:
                rec.nominal_bayar_pertama = rec.nominal_disetujui_anggaran

    @api.depends('nominal_disetujui_usaha', 'kode_anggaran_id.kode_anggaran')
    def _compute_nominal_disetujui(self):
        for record in self:
            record.nominal_disetujui_operasional = record.nominal_final
            record.nominal_disetujui_umum = (
                record.nominal_final if record.kode_anggaran_id and record.kode_anggaran_id.kode_anggaran and record.kode_anggaran_id.kode_anggaran.startswith('6') else 0
            )
            record.nominal_disetujui_total = (
                record.nominal_disetujui_operasional + record.nominal_disetujui_umum
            )
    
    @api.onchange('nominal_disetujui_usaha')
    def _check_nominal_disetujui_usaha(self):
        for record in self:
            if record.nominal_disetujui_usaha > record.nominal_pengajuan:
                formatted_nominal = "{:,.2f}".format(record.nominal_pengajuan)
                record.nominal_disetujui_usaha = 0.0
                return {
                    'warning': {
                        'title': 'Nilai Tidak Valid',
                        'message': f"Nominal disetujui Usaha tidak boleh melebihi Nominal Pengajuan (Rp{formatted_nominal}). Nilai telah direset ke 0."
                    }
                }
    
    @api.constrains('nominal_disetujui_anggaran', 'nominal_pengajuan')
    def _check_nominal_disetujui_anggaran(self):
        for record in self:
            if record.nominal_disetujui_anggaran > record.nominal_pengajuan:
                raise ValidationError("Nominal disetujui Anggaran tidak boleh melebihi Nominal Pengajuan.")
    
    @api.constrains('nominal_bayar_pertama', 'nominal_pengajuan')
    # @api.constrains('nominal_disetujui_keuangan', 'nominal_pengajuan')
    def _check_nominal_disetujui_keuangan(self):
        for record in self:
            if record.nominal_bayar_pertama > record.nominal_pengajuan:
                raise ValidationError("Nominal disetujui Keuangan tidak boleh melebihi Nominal Pengajuan.")


    @api.model
    def init(self):
        existing_kkhc_line_ids = self.search([]).mapped('kkhc_line_id')
        new_kkhc_lines = self.env['account.keuangan.kkhc.line'].search([('id', 'not in', existing_kkhc_line_ids.ids)])
        for kkhc_line in new_kkhc_lines:
            self.create({'kkhc_line_id': kkhc_line.id})

    # new onchanges disetujui 3 divs 
    @api.onchange('nominal_disetujui_usaha')
    def _onchange_nominal_disetujui_usaha(self):
        if self.nominal_disetujui_usaha and self.pagu_limit and self.nominal_disetujui_usaha > self.pagu_limit:
            return {
                'warning': {
                    'title': "Nilai Tidak Valid",
                    'message': "Nominal Disetujui Divisi Usaha/Umum tidak boleh melebihi dari Pagu Limit (%.2f)" % self.pagu_limit,
                }
            }

    @api.onchange('nominal_disetujui_anggaran')
    def _onchange_nominal_disetujui_anggaran(self):
        if self.nominal_disetujui_anggaran and self.pagu_limit and self.nominal_disetujui_anggaran > self.pagu_limit:
            return {
                'warning': {
                    'title': "Nilai Tidak Valid",
                    'message': "Nominal Disetujui Divisi Anggaran tidak boleh melebihi dari Pagu Limit (%.2f)" % self.pagu_limit,
                }
            }

    @api.onchange('nominal_bayar_pertama')
    # @api.onchange('nominal_disetujui_keuangan')
    def _onchange_nominal_disetujui_keuangan(self):
        if self.nominal_bayar_pertama and self.pagu_limit and self.nominal_bayar_pertama > self.pagu_limit:
            return {
                'warning': {
                    'title': "Nilai Tidak Valid",
                    'message': "Nominal Disetujui Divisi Keuangan tidak boleh melebihi dari Pagu Limit (%.2f)" % self.pagu_limit,
                }
            }

    # def write(self, vals):
    #     res = super(AccountMonitorKKHCLine, self).write(vals)
    #     user_level = self.env.user.level
    #     if res:
    #         rejected_lines = []
    #         for record in self:

    #             # !! always re-update divisions offers !!
    #             if record.nominal_disetujui_usaha != record.kkhc_line_id.nominal_disetujui_divisi:
    #                 record.nominal_disetujui_usaha = record.kkhc_line_id.nominal_disetujui_divisi

    #             if 'nominal_disetujui_usaha' in vals and vals['nominal_disetujui_usaha'] != 0.0:
    #                 record.nominal_final = vals['nominal_disetujui_usaha']
    #                 record.is_locked_usaha = False

    #             # anggaran login
    #             if 'nominal_disetujui_anggaran' in vals and vals['nominal_disetujui_anggaran'] != 0.0:
    #                 print("VALS IN SECOND IF", vals)
    #                 record.nominal_final = vals['nominal_disetujui_anggaran']
    #                 record.is_locked_anggaran = False

    #             # keuangan login
    #             if 'nominal_bayar_pertama' in vals and vals['nominal_bayar_pertama'] != 0.0:
    #                 print("VALS IN THIRD IF", vals)
    #                 record.nominal_final = record.nominal_disetujui_anggaran
    #                 record.nominal_bayar_kedua = record.nominal_disetujui_anggaran - vals['nominal_bayar_pertama']
    #                 record.is_locked_keuangan = False

    #             else:
    #                 return {
    #                     'type': 'ir.actions.client',
    #                     'tag': 'display_notification',
    #                     'params': {
    #                         'title': 'Me-refresh halaman...',
    #                         'message': 'Anda tidak berhak untuk membayar nota dinas!',
    #                         'type': 'warning',
    #                         'sticky': False,
    #                     }
    #                 }
    #                 #     raise ValidationError('Anda tidak berhak untuk membayar nota dinas!')
                
    #             # keuangan login too
    #             if 'nominal_bayar_pertama' in vals and 'nominal_bayar_kedua' not in vals:
    #                 print("IS REC EXISTS?", record)
    #                 print("IS REC EXISTS?", record.kkhc_id.name)
    #                 print("IS REC EXISTS?", record.nominal_disetujui_anggaran)
    #                 print("IS REC EXISTS?", record.nominal_final)
    #                 print("IS REC EXISTS?", record.nominal_pengajuan)
    #                 print("VALS IN FIFTH IF", vals)
    #                 if self.env.user.level == 'keuangan':
    #                     if vals['nominal_bayar_pertama'] != 0.0:
    #                         record.nominal_final = record.nominal_disetujui_anggaran
    #                         record.kkhc_line_id.nominal_disetujui = vals['nominal_bayar_pertama']
    #                         record.nominal_bayar_kedua = record.nominal_disetujui_anggaran - vals['nominal_bayar_pertama']
    #                         record.kkhc_line_id.sisa_pengajuan = record.kkhc_line_id.nominal_disetujui - vals['nominal_bayar_pertama']

    #             else:
    #             #     raise ValidationError('Anda tidak berhak untuk membayar nota dinas!')
    #                 return {
    #                     'type': 'ir.actions.client',
    #                     'tag': 'display_notification',
    #                     'params': {
    #                         'title': 'Me-refresh halaman...',
    #                         'message': 'Anda tidak berhak untuk membayar nota dinas!',
    #                         'type': 'warning',
    #                         'sticky': False,
    #                     }
    #                 }

    #             if 'nominal_bayar_kedua' in vals and 'nominal_bayar_pertama' not in vals:
    #                 if self.env.user.level == 'keuangan':
    #                     if vals['nominal_bayar_kedua'] != 0.0 or record.nominal_bayar_kedua != 0.0:
    #                         record.active = False
    #                         return {
    #                             'type': 'ir.actions.client',
    #                             'tag': 'display_notification',
    #                             'params': {
    #                                 'title': 'Me-refresh Halaman...',
    #                                 'message': 'Item ini sudah lunas dan dibayar oleh Kepala Divisi Keuangan. Harap tunggu, browser sedang memperbarui data.',
    #                                 'type': 'warning',
    #                                 'sticky': False,
    #                             }
    #                         }

    #             else:
    #                 return {
    #                     'type': 'ir.actions.client',
    #                     'tag': 'display_notification',
    #                     'params': {
    #                         'title': 'Me-refresh halaman...',
    #                         'message': 'Anda tidak berhak untuk membayar nota dinas!',
    #                         'type': 'warning',
    #                         'sticky': False,
    #                     }

    #                     }
    #                 #     raise ValidationError('Anda tidak berhak untuk membayar nota dinas!')

    #     return res


    def write(self, vals):
        user_level = self.env.user.level
        res = super(AccountMonitorKKHCLine, self).write(vals)
        
        for record in self:
            # !! ------ SELALU AWALI DENGAN MENGUPDATE NOMINAL VERIFIKASI DIVISI ------ !!
            if record.nominal_disetujui_usaha != record.kkhc_line_id.nominal_disetujui_divisi:
                record.nominal_disetujui_usaha = record.kkhc_line_id.nominal_disetujui_divisi

            # ------ LOGIC UNTUK USER USAHA/UMUM (LEVEL 1) ------
            if user_level == 'usaha':
                # User usaha hanya boleh edit nominal_disetujui_usaha
                # if 'nominal_disetujui_anggaran' in vals or 'nominal_bayar_pertama' in vals:
                #     raise ValidationError("Anda (Usaha/Umum) tidak boleh mengedit nilai Anggaran/Keuangan!")
                
                # Auto-set nilai ke nominal_disetujui_anggaran & nominal_final
                if 'nominal_disetujui_usaha' in vals:
                    record.nominal_disetujui_anggaran = vals['nominal_disetujui_usaha']
                    record.nominal_final = vals['nominal_disetujui_usaha']
            
            # ------ LOGIC UNTUK USER ANGGARAN (LEVEL 2) ------
            elif user_level == 'anggaran':
                # User anggaran hanya boleh edit nominal_disetujui_anggaran
                # if 'nominal_disetujui_usaha' in vals or 'nominal_bayar_pertama' in vals:
                #     raise ValidationError("Anda (Anggaran) tidak boleh mengedit nilai Usaha/Keuangan!")
                
                # Auto-set nilai ke nominal_bayar_pertama & nominal_final
                if 'nominal_disetujui_anggaran' in vals:
                    record.nominal_bayar_pertama = vals['nominal_disetujui_anggaran']
                    record.nominal_final = vals['nominal_disetujui_anggaran']
            
            # ------ LOGIC UNTUK USER KEUANGAN (LEVEL 3) ------
            elif user_level == 'keuangan':
                # User keuangan hanya boleh edit nominal_bayar_pertama
                # if 'nominal_disetujui_usaha' in vals or 'nominal_disetujui_anggaran' in vals:
                #     raise ValidationError("Anda (Keuangan) tidak boleh mengedit nilai Usaha/Anggaran!")
                
                # Tidak auto-set ke nominal_final, karena nominal_final = nominal_anggaran, langsung realisasi ke KKHC
                if 'nominal_bayar_pertama' in vals:
                    # record.nominal_bayar_kedua = record.nominal_disetujui_anggaran - vals['nominal_bayar_pertama']
                    record.nominal_bayar_kedua = record.nominal_disetujui_anggaran - vals['nominal_bayar_pertama']
                    record.kkhc_line_id.nominal_disetujui = record.nominal_disetujui_anggaran

                # if 'nominal_bayar_kedua' in vals and vals['nominal_bayar_kedua'] != 0.0:
                    # record.nominal_bayar_kedua = 0.0
                    # record.active = False

        return res

    @api.model
    def default_get(self, fields):
        res = super(AccountMonitorKKHCLine, self).default_get(fields)
        if self.env.user.level == 'anggaran' and 'nominal_disetujui_anggaran' in fields:
            res['nominal_disetujui_anggaran'] = res.get('nominal_disetujui_usaha', 0.0)
            
        return res

    def read(self, fields=None, load='_classic_read'):
        records = super(AccountMonitorKKHCLine, self).read(fields, load)

        if fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                if record.nominal_disetujui_usaha != record.kkhc_line_id.nominal_disetujui_divisi:
                    record.nominal_disetujui_usaha = record.kkhc_line_id.nominal_disetujui_divisi

                    if record.nominal_disetujui_anggaran == 0.0:
                        record.nominal_disetujui_anggaran = record.nominal_disetujui_usaha
                    if record.nominal_bayar_pertama == 0.0:
                        record.nominal_bayar_pertama = record.nominal_disetujui_anggaran

                record._compute_type()
                record._compute_nominal_disetujui()
                record._compute_total_per_cabang()
                record._compute_nominal_disetujui_anggaran_default()
                record._compute_nominal_disetujui_keuangan_default()
                record._compute_user_level()

        return records
    
    @api.onchange('nodin_bod_id')
    def _onchange_nodin_bod_id(self):
        if self.nodin_id and self.nodin_bod_id:
            self.nodin_bod_id.tanggal_pengajuan = self.nodin_id.tanggal_pengajuan
            self.nodin_bod_id.document_ids = self.nodin_id.document_ids.ids

            self.nodin_bod_id.document_ids.write({'nodin_bod_id': self.nodin_bod_id.id})

    @api.onchange('nominal_bayar_kedua')
    def _onchange_nominal_bayar_kedua(self):
        for line in self:
            if line.nominal_bayar_pertama == 0.0 and not line.tgl_bayar_pertama:
                raise ValidationError('Termin pertama masih kosong. Mohon untuk menggunakan termin pertama terlebih dahulu!')

    def remove_duplicates(self):
        all_records = self.env['account.keuangan.monitor.kkhc.line'].search([])
        seen_ids = set()
        duplicates = []
        for record in all_records:
            if record.kkhc_line_id.id in seen_ids:
                duplicates.append(record.id)
            else:
                seen_ids.add(record.kkhc_line_id.id)
        if duplicates:
            self.env['account.keuangan.monitor.kkhc.line'].browse(duplicates).unlink()
        
    @api.depends('kode_anggaran_id.kode_anggaran')    
    def _compute_type(self):
        for record in self:
            kode = record.kode_anggaran_id.kode_anggaran if record.kode_anggaran_id and record.kode_anggaran_id.kode_anggaran else ''
            if not kode:
                _logger.warning("Record %s has no kode_anggaran_id or kode_anggaran", record)
            if kode.startswith('5'):
                record.type = 'usaha'
            elif kode.startswith('6'):
                record.type = 'umum'
            elif kode.startswith('4'):
                record.type = 'usaha'
            else:
                record.type = 'usaha'

# class NotaDinasRejectedLine(models.Model):
#     _name = 'account.keuangan.monitor.kkhc.line.rejected'
#     _description = 'Rejected Nodin Lines'

#     active = fields.Boolean(string='Active', default=True)
#     kkhc_line_id = fields.Many2one('account.keuangan.kkhc.line', string='Item KKHC')
#     kkhc_id = fields.Many2one('account.keuangan.kkhc', string='No. KKHC')
#     nodin_id = fields.Many2one('account.keuangan.nota.dinas', string='No. Nodin')
#     nodin_bod_id = fields.Many2one('account.keuangan.nota.dinas.bod', string='No. Nodin BoD')
#     branch_id = fields.Many2one('res.branch', string='Cabang')
#     kode_anggaran_id = fields.Many2one('account.keuangan.kode.anggaran', string='Kode Anggaran')
#     deskripsi = fields.Text(string='Deskripsi Penggunaan')
#     account_code_id = fields.Many2one('account.account', string='COA')
#     currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env['res.currency'].search([('name', '=', 'IDR')], limit=1))
#     nominal_pengajuan = fields.Float(string='Nominal Pengajuan', store=True, tracking=True)
#     nominal_disetujui = fields.Float(string='Nominal Disetujui', store=True, tracking=True)

#     uraian = fields.Text(string='Uraian Penggunaan')
#     jumlah_biaya = fields.Float(string='Jumlah Biaya', store=True, tracking=True, default=0.0)
#     periode_kkhc_start = fields.Date(string='Awal Periode')
#     periode_kkhc_end = fields.Date(string='Akhir Periode')
#     nominal_disetujui_usaha = fields.Float(string='Usaha/Umum')
