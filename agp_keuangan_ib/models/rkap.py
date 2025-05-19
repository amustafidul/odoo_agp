from odoo import models, fields, api, _
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)


class Rkap(models.Model):
    _name = 'account.keuangan.rkap'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Rencana Kerja dan Anggaran Perusahaan'

    name = fields.Char(string='RKAP Number', required=True, copy=True, readonly=False, default=lambda self: _('New'), tracking=True)
    branch_id = fields.Many2one(
        'res.branch',
        string='Nama Cabang',
        readonly=True,
        default=lambda self: self.env.user.branch_id
    )
    ref = fields.Char(string='Nomor Referensi', tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    
    tanggal_pengajuan= fields.Date(string='Tanggal Pengajuan', required=True, tracking=True)
    tanggal_disetujui= fields.Date(string='Tanggal Disetujui', tracking=True)
    jumlah_pemasukan = fields.Float(string='Jumlah Pemasukan', compute='_compute_totals', store=True, tracking=True)
    sisa_pemasukan = fields.Float(string='Sisa Pemasukan', compute='_compute_sisa_anggaran', store=True, tracking=True)
    jumlah_pengeluaran = fields.Float(string='Jumlah Pengeluaran', compute='_compute_totals', store=True, tracking=True)
    sisa_pengeluaran = fields.Float(string='Sisa Pengeluaran', compute='_compute_sisa_anggaran', store=True, tracking=True)
    pemakaian_pemasukan = fields.Float(string='Realisasi Pemasukan', compute='_compute_pemakaian_anggaran', store=True, tracking=True)
    pemakaian_pengeluaran = fields.Float(string='Realisasi Pengeluaran', compute='_compute_pemakaian_anggaran', store=True, tracking=True)

    rkap_line_ids = fields.One2many('account.keuangan.rkap.line', 'rkap_id', string='RKAP Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')

    def read(self, fields=None, load='_classic_read'):
        records = super(Rkap, self).read(fields, load)

        if fields:
            self._reorder_rkap_lines()

        return records

    def _get_years(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in range(current_year - 1, current_year + 10)]
    
    tahun_anggaran = fields.Selection(selection=_get_years, string="Tahun Anggaran", required=True, tracking=True)

    def _reorder_rkap_lines(self):
        for rec in self:
            lines = rec.rkap_line_ids.sorted('id')
            for idx, line in enumerate(lines, start=1):
                line.sequence = idx

    @api.depends('rkap_line_ids.nominal', 'rkap_line_ids.kode_anggaran_id.account_type')
    def _compute_totals(self):
        for record in self:
            pemasukan_total = 0.0
            pengeluaran_total = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.account_type == 'masuk':
                    pemasukan_total += line.nominal
                elif line.kode_anggaran_id.account_type == 'keluar':
                    pengeluaran_total += line.nominal
            record.jumlah_pemasukan = pemasukan_total
            record.jumlah_pengeluaran = pengeluaran_total

    @api.depends('rkap_line_ids.realisasi', 'rkap_line_ids.kode_anggaran_id.account_type')
    def _compute_sisa_anggaran(self):
        for record in self:
            pemasukan_total = 0.0
            pengeluaran_total = 0.0
            for line in record.rkap_line_ids:
                if line.kode_anggaran_id.account_type == 'masuk':
                    pemasukan_total += line.realisasi
                elif line.kode_anggaran_id.account_type == 'keluar':
                    pengeluaran_total += line.realisasi
            record.sisa_pemasukan = pemasukan_total
            record.sisa_pengeluaran = pengeluaran_total

    @api.depends('jumlah_pemasukan', 'sisa_pemasukan')
    def _compute_pemakaian_anggaran(self):
        for record in self:
            record.pemakaian_pemasukan = record.jumlah_pemasukan - record.sisa_pemasukan
            record.pemakaian_pengeluaran = record.jumlah_pengeluaran - record.sisa_pengeluaran


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):            
            # Get the date details
            date_str = vals.get('date', fields.Date.context_today(self))
            date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
            year = date_obj.strftime('%Y')
            month = int(date_obj.strftime('%m'))
            roman_month = self._to_roman(month)
            
            # Get the default branch of the user
            user = self.env.user
            default_branch = user.branch_id[0] if user.branch_id else None
            branch_code = default_branch.code if default_branch else 'KOSONG'
            
            # Get the department code of the user
            department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
            # Generate the custom sequence number
            sequence_code = self.env['ir.sequence'].next_by_code('sequence.keuangan.rkap') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/RKAP-{branch_code}/{roman_month}/{year}'
        
        return super(Rkap, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')


class RkapLine(models.Model):
    _name = 'account.keuangan.rkap.line'
    _description = 'Rencana Kerja dan Anggaran Perusahaan Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='No.', store=True)
    rkap_id = fields.Many2one(
        'account.keuangan.rkap',
        string='RKAP',
        ondelete='cascade'
    )
    kode_anggaran_id = fields.Many2one(
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran',
        required=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one('res.partner', string="Partner", tracking=True)
    branch_id = fields.Many2one(related='rkap_id.branch_id', string='Branch', store=True, readonly=True)
    deskripsi_penggunaan = fields.Text(string='Tujuan Penggunaan Anggaran', tracking=True)
    nominal = fields.Float(string='Nominal Anggaran', required=True, tracking=True)
    deskripsi = fields.Text(string='Deskripsi Anggaran', readonly=True, tracking=True)
    account_code_id = fields.Many2one('account.account', string='Account Code', readonly=True, tracking=True)
    realisasi = fields.Float(string='Sisa Anggaran', compute='_compute_realisasi', store=True, tracking=True)
    pemakaian_anggaran = fields.Float(string='Realisasi Anggaran', store=True, tracking=True)
    header_state = fields.Selection(string='RKAP State', related='rkap_id.state')
    
    @api.onchange('kode_anggaran_id')
    def _onchange_kode_anggaran_id(self):
        if self.kode_anggaran_id:
            self.deskripsi = self.kode_anggaran_id.deskripsi
            self.account_code_id = self.kode_anggaran_id.account_code_id
        else:
            self.deskripsi = False
            self.account_code_id = False
    
    @api.onchange('kode_anggaran_id')
    def _onchange_kode_anggaran(self):
        used_codes = self.rkap_id.rkap_line_ids.mapped('kode_anggaran_id.id')
        if used_codes:
            return {'domain': {'kode_anggaran_id': [('id', 'not in', used_codes)]}}
        else:
            return {'domain': {'kode_anggaran_id': []}}

    
    @api.onchange('kode_anggaran_id')
    def _onchange_kode_anggaran_id(self):
        if self.kode_anggaran_id:
            self.deskripsi = self.kode_anggaran_id.deskripsi
            self.account_code_id = self.kode_anggaran_id.account_code_id
        else:
            self.deskripsi = False
            self.account_code_id = False

    # === Utility method to reorder sequence ===
    def reorder_sequence(self):
        rkap_groups = defaultdict(list)
        for line in self.search([], order='rkap_id, id'):
            rkap_groups[line.rkap_id.id].append(line)

        for lines in rkap_groups.values():
            for idx, line in enumerate(lines, start=1):
                line.sequence = idx

    def unlink(self):
        rkap_ids = self.mapped('rkap_id')
        result = super().unlink()
        rkap_ids._reorder_rkap_lines()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for vals, record in zip(vals_list, records):
            if vals.get('kode_anggaran_id'):
                kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
                record.write({
                    'deskripsi': kode_anggaran.deskripsi,
                    'account_code_id': kode_anggaran.account_code_id.id,
                })

        records.mapped('rkap_id')._reorder_rkap_lines()

        return records

    def write(self, vals):
        if vals.get('kode_anggaran_id'):
            kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
            vals.update({
                'deskripsi': kode_anggaran.deskripsi,
                'account_code_id': kode_anggaran.account_code_id.id,
            })
        return super(RkapLine, self).write(vals)

    # @api.depends('kode_anggaran_id', 'branch_id')
    # def _compute_realisasi(self):
    #     for record in self:
    #         if record.kode_anggaran_id and record.branch_id:
    #             # Get the necessary IDs for the query
    #             kode_anggaran_id = record.kode_anggaran_id.id
    #             branch_id = record.branch_id.id
                
    #             # Log the details of the current record for debugging purposes
    #             # _logger.info(f"Computing realisasi for record {record.id} with kode_anggaran_id {record.kode_anggaran_id.id} and branch_id {record.branch_id.name}")
                
    #             # SQL Query to fetch matching saldo record
    #             query = """
    #                 SELECT saldo.saldo
    #                 FROM account_keuangan_saldo saldo
    #                 WHERE saldo.kode_anggaran_id = %s
    #                 AND saldo.branch_id = %s
    #                 LIMIT 1
    #             """
                
    #             # Execute the query
    #             self.env.cr.execute(query, (kode_anggaran_id, branch_id))
                
    #             # Fetch the result
    #             result = self.env.cr.fetchone()

    #             # Log the result
    #             if result:
    #                 # _logger.info(f"Saldo found for record {record.id}: {result[0]}")
    #                 record.realisasi = result[0]
    #             else:
    #                 # _logger.info(f"No saldo found for record {record.id}. Setting realisasi to 0.")
    #                 record.realisasi = 0.0
    #         else:
    #             # _logger.warning(f"Record {record.id} is missing either kode_anggaran_id or branch_id. Setting realisasi to 0.")
    #             record.realisasi = 0.0


    @api.depends('nominal', 'pemakaian_anggaran')
    def _compute_realisasi(self):
        for line in self:
            # Menghitung realisasi sebagai selisih antara nominal dan pemakaian_anggaran
            line.realisasi = line.nominal - line.pemakaian_anggaran

