from odoo import models, fields, api, _
from collections import defaultdict
from datetime import date, datetime, timedelta
import pytz
import pendulum

from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class Kkhc(models.Model):
    _name = 'account.keuangan.kkhc'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'KKHC'

    name = fields.Char(string='KKHC Number', required=True, copy=True, readonly=False, default=lambda self: _('Nomor KKHC akan terisi otomatis...'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Diajukan oleh GM Cabang'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')
    nama_anggaran = fields.Char(string='Nama Anggaran', tracking=True)
    branch_id = fields.Many2one(
        'res.branch',
        string='Nama Cabang',
        readonly=True,
        default=lambda self: self.env.user.branch_id
    )
    nomor_referensi = fields.Char(string='Nomor Referensi', tracking=True)
    kata_pengantar = fields.Text(string='Kata Pengantar', tracking=True)
    tanggal_pengajuan = fields.Date(string='Tanggal Pengajuan', default=fields.Date.context_today)
    jumlah_ajuan_anggaran = fields.Float(string='Jumlah Ajuan Anggaran', compute='_compute_jumlah_ajuan_anggaran', store=True, tracking=True)
    tanggal_disetujui = fields.Date(string='Tanggal Disetujui', tracking=True)
    jumlah_pemasukan_pengajuan = fields.Float(string='Jumlah Pemasukan Pengajuan', compute='_compute_total_pengajuan', store=True, tracking=True)
    jumlah_pemasukan_disetujui = fields.Float(string='Jumlah Pemasukan Disetujui', compute='_compute_total_disetujui', store=True, tracking=True)
    jumlah_pengeluaran_pengajuan = fields.Float(string='Jumlah Pengeluaran Pengajuan', compute='_compute_total_pengajuan', store=True, tracking=True)
    jumlah_pengeluaran_disetujui = fields.Float(string='Jumlah Pengeluaran Disetujui', compute='_compute_total_disetujui', store=True, tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    kkhc_line_ids = fields.One2many('account.keuangan.kkhc.line', 'kkhc_id', string='KKHC Lines', ondelete='cascade', tracking=True)
    kode_anggaran_id = fields.Many2one(
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran'
    )
    is_pending = fields.Boolean(
        string='Pending',
        compute='_compute_is_pending',
        store=True,
    )
    total_diajukan = fields.Float(string='Total', compute='_compute_total_diajukan', store=True, tracking=True)
    total_disetujui = fields.Float(string='Total', compute='_compute_total_disetujui', store=True, tracking=True)

    def read(self, fields=None, load='_classic_read'):
        records = super(Kkhc, self).read(fields, load)

        if fields:
            self._reorder_kkhc_lines()

        return records

    def _reorder_kkhc_lines(self):
        for rec in self:
            lines = rec.kkhc_line_ids.sorted('id')
            for idx, line in enumerate(lines, start=1):
                line.sequence = idx

    @api.depends('kkhc_line_ids.nominal_pengajuan')
    def _compute_total_diajukan(self):
        for record in self:
            record.total_diajukan = sum(line.nominal_pengajuan for line in record.kkhc_line_ids)

    @api.depends('kkhc_line_ids.nominal_disetujui')
    def _compute_total_disetujui(self):
        for record in self:
            record.total_disetujui = sum(line.nominal_disetujui for line in record.kkhc_line_ids)
    
    # old pytz based
    # def _get_week_of_month(self, target_date):
    #     first_day_of_month = target_date.replace(day=1)
    #     first_weekday = first_day_of_month.weekday()
        
    #     first_monday = first_day_of_month if first_weekday == 0 else first_day_of_month + timedelta(days=(7 - first_weekday))

    #     if first_monday > target_date:
    #         first_monday -= timedelta(weeks=1)

    #     return ((target_date - first_monday).days // 7) + 1

    # new pendulum-based
    def _get_week_of_month(self, target_date):
        # Make sure target_date is timezone-aware in Jakarta
        if not isinstance(target_date, pendulum.DateTime):
            target_date = pendulum.instance(target_date).in_tz('Asia/Jakarta')
        
        first_day = target_date.start_of('month')
        # Find Monday of the week of the 1st
        first_monday = first_day.start_of('week')  # week starts Monday in pendulum

        if first_monday.month != first_day.month:
            # if the first Monday is still in previous month, move forward 1 week
            first_monday = first_monday.add(weeks=1)

        # Now calculate the week difference
        return ((target_date - first_monday).days // 7) + 1

    @api.depends('kkhc_line_ids.status_anggaran')
    def _compute_is_pending(self):
        for record in self:
            record.is_pending = any(line.status_anggaran == 'pending' for line in record.kkhc_line_ids)

    @api.depends('ditujukan_kepada')
    def _compute_alamat_perusahaan(self):
        for record in self:
            if record.ditujukan_kepada:
                record.alamat_perusahaan = record.ditujukan_kepada.contact_address
            else:
                record.alamat_perusahaan = ''

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        if self.branch_id:
            return {'domain': {'sub_branch_ids': [('id', 'in', self.branch_id.sub_branch_ids.ids)]}}
        else:
            return {'domain': {'sub_branch_ids': []}}

    @api.model
    def action_confirm(self):
        self.state = 'approved'
        return True

    @api.model
    def action_print(self):
        return self.env.ref('agp_keuangan_ib.report_invoice').report_action(self)

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', _('Nomor KKHC akan terisi otomatis...')) == _('Nomor KKHC akan terisi otomatis...'):            
    #         # Get the date details
    #         date_str = vals.get('date', fields.Date.context_today(self))
    #         date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
    #         year = date_obj.strftime('%Y')
    #         month = int(date_obj.strftime('%m'))
    #         roman_month = self._to_roman(month)
            
    #         # Get the default branch of the user
    #         user = self.env.user
    #         default_branch = user.branch_id[0] if user.branch_id else None
    #         branch_code = default_branch.code if default_branch else 'KOSONG'
            
    #         # Get the department code of the user
    #         department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
    #         # Generate the custom sequence number
    #         sequence_code = self.env['ir.sequence'].next_by_code('sequence.keuangan.kkhc') or '0000'

    #         # Generate the custom sequence
    #         vals['name'] = f'{sequence_code}/KKHC-{branch_code}/{roman_month}/{year}'

    #     jakarta_tz = pytz.timezone('Asia/Jakarta')
    #     today = datetime.now(jakarta_tz).date()
    #     week_number = self._get_week_of_month(today)
    #     month_roman = self._to_roman(today.month)
    #     year = today.year
    #     vals['nama_anggaran'] = f"Week {week_number} - {month_roman}/{year}"

    #     return super(Kkhc, self).create(vals)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nomor KKHC akan terisi otomatis...')) == _('Nomor KKHC akan terisi otomatis...'):            
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
            
            sequence_code = self.env['ir.sequence'].next_by_code('sequence.keuangan.kkhc') or '0000'
            vals['name'] = f'{sequence_code}/KKHC-{branch_code}/{roman_month}/{year}'

        # SIMPLIFIED with pendulum
        today = pendulum.now('Asia/Jakarta')
        week_number = self._get_week_of_month(today)
        month_roman = self._to_roman(today.month)
        year = today.year
        vals['nama_anggaran'] = f"Week {week_number} - {month_roman}/{year}"

        return super(Kkhc, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')

    
    @api.depends('kkhc_line_ids.nominal_pengajuan')
    def _compute_jumlah_ajuan_anggaran(self):
        for record in self:
            record.jumlah_ajuan_anggaran = sum(line.nominal_pengajuan for line in record.kkhc_line_ids)

    
    @api.depends('kkhc_line_ids.nominal_pengajuan', 'kkhc_line_ids.kode_anggaran_id.account_type')
    def _compute_total_pengajuan(self):
        for record in self:
            pemasukan_total = 0.0
            pengeluaran_total = 0.0
            for line in record.kkhc_line_ids:
                if line.kode_anggaran_id.account_type == 'masuk':
                    pemasukan_total += line.nominal_pengajuan
                elif line.kode_anggaran_id.account_type == 'keluar':
                    pengeluaran_total += line.nominal_pengajuan
            record.jumlah_pemasukan_pengajuan = pemasukan_total
            record.jumlah_pengeluaran_pengajuan = pengeluaran_total


    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.account_type')
    def _compute_total_disetujui(self):
        for record in self:
            pemasukan_total = 0.0
            pengeluaran_total = 0.0
            for line in record.kkhc_line_ids:
                if line.kode_anggaran_id.account_type == 'masuk':
                    pemasukan_total += line.nominal_disetujui
                elif line.kode_anggaran_id.account_type == 'keluar':
                    pengeluaran_total += line.nominal_disetujui
            record.jumlah_pemasukan_disetujui = pemasukan_total
            record.jumlah_pengeluaran_disetujui = pengeluaran_total

    def print_kkhc(self):
        return self.env.ref('agp_keuangan_ib.report_kkhc').report_action(self)

    def get_report_values(self, docids, data=None):
        docs = self.env['account.keuangan.kkhc'].browse(docids)
        return {
            'docs': docs,
        }

    def get_penerimaan_pengeluaran(self):
        penerimaan = []
        pengeluaran = []

        for line in self.kkhc_line_ids:
            if line.kode_anggaran_id.account_type == 'masuk':
                penerimaan.append({
                    'bank_account': line.bank_account_id,
                    'nominal_disetujui': line.nominal_disetujui or 0  
                })
            elif line.kode_anggaran_id.account_type == 'keluar':
                pengeluaran.append({
                    'bank_account': line.bank_account_id,
                    'nominal_disetujui': line.nominal_disetujui or 0

                })

        return {
            'penerimaan': penerimaan,
            'pengeluaran': pengeluaran,
        }

    def action_confirm(self):
        for record in self:
            for line in record.kkhc_line_ids:
                if line.nominal_disetujui > line.kode_anggaran_id.saldo:
                    raise ValidationError(_('Saldo tidak mencukupi untuk kode anggaran %s' % line.kode_anggaran_id.name))
                line.kode_anggaran_id._reduce_saldo(line.nominal_disetujui)
            record.state = 'approved'

    @api.model
    def get_report_values(self, docids, data=None):
        docs = self.env['account.keuangan.kkhc'].browse(docids)
        
        kelompok_data = defaultdict(list)
        
        for line in docs.kkhc_line_ids:
            if line.kode_anggaran_id:
                kelompok = line.kode_anggaran_id.kelompok
                kelompok_data[kelompok].append(line)
        
        return {
            'doc_ids': docids,
            'doc_model': 'account.keuangan.kkhc',
            'docs': docs,
            'kelompok_data': kelompok_data,
        }


class KkhcLine(models.Model):
    _name = 'account.keuangan.kkhc.line'
    _description = 'KKHC Line'
    _rec_name = 'line_name'
    _order = 'sequence, id'

    sequence = fields.Integer(string='No.', store=True)
    line_name = fields.Char(compute='_compute_line_name', store=True, readonly=False)
    kkhc_id = fields.Many2one('account.keuangan.kkhc', string='KKHC', required=True, ondelete='cascade', tracking=True)
    deskripsi_penggunaan = fields.Text(string='Tujuan Penggunaan Anggaran', tracking=True)
    bank_account_id = fields.Many2one('res.partner.bank', string='Rekening', tracking=True)
    nominal_pengajuan = fields.Float(string='Nominal Pengajuan', store=True, tracking=True)
    available_kode_anggaran_ids = fields.Many2many(
        'account.keuangan.kode.anggaran',
        compute='_compute_available_kode_anggaran_ids',
        string='Available Kode Anggaran',
    )

    @api.depends('kkhc_id.branch_id')
    def _compute_available_kode_anggaran_ids(self):
        for line in self:
            if not line.kkhc_id.branch_id:
                line.available_kode_anggaran_ids = [(5, 0, 0)]  # Empty
                continue
            self._cr.execute("""
                SELECT DISTINCT ka.id
                FROM account_keuangan_rkap_line rl
                JOIN account_keuangan_kode_anggaran ka ON ka.id = rl.kode_anggaran_id
                WHERE rl.branch_id = %s
            """, [line.kkhc_id.branch_id.id])
            ids = [row[0] for row in self._cr.fetchall()]
            line.available_kode_anggaran_ids = [(6, 0, ids)]

    kode_anggaran_id = fields.Many2one(
        'account.keuangan.kode.anggaran',
        string='Kode Anggaran',
        domain="[('id', 'in', available_kode_anggaran_ids)]"
    )

    branch_id = fields.Many2one(related='kkhc_id.branch_id', string='Branch', store=True, readonly=True)
    pagu_limit = fields.Float(string='Pagu Limit', compute='_compute_pagu_limit', store=True, tracking=True)
    unit_penempatan_id = fields.Many2one('hr.employee.unit', string='Divisi', store=True, tracking=True)
    nominal_disetujui = fields.Float(string='Nominal Disetujui', store=True, tracking=True, readonly=True)
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ], string='Status Persetujuan', default='draft', required=True, tracking=True)
    status_pembayaran = fields.Selection([
        ('paid', 'Paid'),
        ('not_paid', 'Not Paid')
    ], string='Status Pembayaran', tracking=True)
    deskripsi = fields.Text(string='Deskripsi Anggaran', readonly=True, store=True, tracking=True)
    account_code_id = fields.Many2one('account.account', string='Account Code', readonly=True, store=True, tracking=True)
    sisa_pengajuan = fields.Float(string='Sisa Pengajuan', store=True, tracking=True)
    state = fields.Selection(related='kkhc_id.state', store=True, tracking=True)
    status_anggaran = fields.Selection([
        ('pending', 'Pending'),
        ('approve', 'Approve'),
        ('reject', 'Reject')
    ], string="Status Anggaran", tracking=True)
    notes = fields.Text(string="Rejection Notes", tracking=True)
    header_state = fields.Selection(string='KKHC State', related='kkhc_id.state')
    kode = fields.Char(string='Kode', related='kode_anggaran_id.kode_anggaran')
    total_nominal_dibayar_pusat = fields.Float(string='Total Disetujui', compute='_compute_total_nominal_dibayar_pusat', store=True)

    @api.depends('kode_anggaran_id', 'account_code_id', 'nominal_disetujui')
    def _compute_total_nominal_dibayar_pusat(self):
        for record in self:
            if record.kode_anggaran_id and record.account_code_id:
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(nominal_disetujui), 0)
                    FROM account_keuangan_kkhc_line
                    WHERE kode_anggaran_id = %s
                    AND account_code_id = %s
                    AND nominal_disetujui != 0
                """, (record.kode_anggaran_id.id, record.account_code_id.id))
                result = self.env.cr.fetchone()
                record.total_nominal_dibayar_pusat = result[0] if result else 0.0
            else:
                record.total_nominal_dibayar_pusat = 0.0

    def read(self, fields=None, load='_classic_read'):
        records = super(KkhcLine, self).read(fields, load)

        if fields:
            self._compute_total_nominal_dibayar_pusat()
            self._compute_available_kode_anggaran_ids()

        return records

    # def _validate_nominal_vs_pagu(self):
    #     for rec in self:
    #         if rec.nominal_pengajuan > rec.pagu_limit:
    #             raise ValidationError(
    #                 f"Nominal Pengajuan (Rp {rec.nominal_pengajuan:,.0f}) tidak boleh melebihi batas Pagu Limit (Rp {rec.pagu_limit:,.0f})."
    #             )

    # @api.constrains('nominal_pengajuan', 'pagu_limit')
    # def _check_nominal_pengajuan(self):
    #     for record in self:
    #         if record.nominal_pengajuan > record.pagu_limit:
    #             _logger.info('# === Logger Input KKHC === #')
    #             _logger.info(f'KKHC Number: {record.kkhc_id.name}')
    #             _logger.info(f'Line Sequence: {record.sequence}')
    #             _logger.info(f'Line Kode: {record.kode_anggaran_id.kode_anggaran}')
    #             _logger.info(f'Line COA: {record.account_code_id.name}')
    #             _logger.info(f'Line Pagu: {record.pagu_limit}')
    #             _logger.info('# === Logger Input KKHC === #')
    #             raise ValidationError("Nominal Pengajuan tidak boleh melebihi batas Pagu Limit KKHC.")

    # === Utility method to reorder sequence ===
    def reorder_sequence(self):
        kkhc_groups = defaultdict(list)
        for line in self.search([], order='kkhc_id, id'):
            kkhc_groups[line.kkhc_id.id].append(line)

        for lines in kkhc_groups.values():
            for idx, line in enumerate(lines, start=1):
                line.sequence = idx

    def unlink(self):
        kkhc_ids = self.mapped('kkhc_id')
        result = super().unlink()
        kkhc_ids._reorder_kkhc_lines()
        return result

    def read(self, fields=None, load='_classic_read'):
        records = super(KkhcLine, self).read(fields, load) or []  # Ensure records is at least an empty list

        if fields and 'kode_anggaran_id' in fields:
            for record_dict in records:
                record = self.browse(record_dict['id'])
                if record.exists():
                    record._compute_line_name()
                    record._compute_pagu_limit()

        return records

    @api.depends(
        'kode_anggaran_id.kode_anggaran',
        'branch_id.name',
        'deskripsi'
    )
    def _compute_line_name(self):
        for record in self:
            kode_anggaran = record.kode_anggaran_id.kode_anggaran or '0000'
            branch_name = record.branch_id.name or 'UNKNOWN BRANCH'
            deskripsi = record.deskripsi or 'NO DESCRIPTION'
            record.line_name = f"{kode_anggaran} - {branch_name} - {deskripsi}"
            
    @api.depends('kode_anggaran_id', 'kkhc_id.branch_id')
    def _compute_pagu_limit(self):
        for line in self:
            if line.kode_anggaran_id and line.kkhc_id and line.kkhc_id.branch_id:
                # Get the necessary IDs for the query
                kode_anggaran_id = line.kode_anggaran_id.id
                branch_id = line.kkhc_id.branch_id.id
                
                # Log the details of the current line and parent Kkhc record
                _logger.info(f"Computing pagu_limit for KkhcLine {line.id} with kode_anggaran_id {line.kode_anggaran_id.id} and branch_id {line.kkhc_id.branch_id.name}")
                
                # SQL Query to fetch matching saldo records
                query = """
                    SELECT saldo.id, saldo.saldo
                    FROM account_keuangan_saldo saldo
                    WHERE saldo.kode_anggaran_id = %s
                    AND saldo.branch_id = %s
                """
                
                # Execute the query
                self.env.cr.execute(query, (kode_anggaran_id, branch_id))
                
                # Fetch the results
                saldo_records = self.env.cr.fetchall()

                # Log the number of records found and the record details
                _logger.info(f"Found {len(saldo_records)} saldo records for kode_anggaran_id {line.kode_anggaran_id.id} and branch_id {line.kkhc_id.branch_id.name}")
                _logger.info(f"Saldo records: {saldo_records}")
                
                # Calculate the total saldo from the fetched records
                if saldo_records:
                    total_saldo = sum(record[1] for record in saldo_records)  # record[1] is the saldo value
                    _logger.info(f"Total saldo for KkhcLine {line.id} is {total_saldo}")
                    line.pagu_limit = total_saldo
                else:
                    _logger.info(f"No saldo records found for KkhcLine {line.id}. Setting pagu_limit to 0.")
                    line.pagu_limit = 0.0
            else:
                _logger.warning(f"KkhcLine {line.id} is missing either kode_anggaran_id or branch_id. Setting pagu_limit to 0.")
                line.pagu_limit = 0.0

    @api.onchange('kode_anggaran_id')
    def _onchange_kode_anggaran_id(self):
        if self.kode_anggaran_id:
            # Mengisi deskripsi dan account_code_id dari Kode Anggaran yang dipilih
            self.deskripsi = self.kode_anggaran_id.deskripsi
            self.account_code_id = self.kode_anggaran_id.account_code_id
            self.unit_penempatan_id = self.kode_anggaran_id.unit_penempatan_id
        else:
            # Kosongkan field jika tidak ada Kode Anggaran yang dipilih
            self.deskripsi = False
            self.account_code_id = False
            self.unit_penempatan_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('kode_anggaran_id'):
                kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
                vals.update({
                    'deskripsi': kode_anggaran.deskripsi,
                    'account_code_id': kode_anggaran.account_code_id.id,
                    'unit_penempatan_id': kode_anggaran.unit_penempatan_id.id
                })

        records = super(KkhcLine, self).create(vals_list)

        for record in records:
            if record.kode_anggaran_id:
                rkap_lines = self.env['account.keuangan.rkap.line'].search([
                    ('kode_anggaran_id', '=', record.kode_anggaran_id.id),
                    ('rkap_id.branch_id', '=', record.kkhc_id.branch_id.id)
                ])
                rkap_lines._compute_realisasi()

        records.mapped('kkhc_id')._reorder_kkhc_lines()

        # records._validate_nominal_vs_pagu()

        return records

    def write(self, vals):
        if vals.get('kode_anggaran_id'):
            kode_anggaran = self.env['account.keuangan.kode.anggaran'].browse(vals['kode_anggaran_id'])
            vals.update({
                'deskripsi': kode_anggaran.deskripsi,
                'account_code_id': kode_anggaran.account_code_id.id,
                'unit_penempatan_id': kode_anggaran.unit_penempatan_id.id
            })

        res = super(KkhcLine, self).write(vals)

        if 'kode_anggaran_id' in vals or 'kkhc_id' in vals:
            for record in self:
                if record.kode_anggaran_id:
                    rkap_lines = self.env['account.keuangan.rkap.line'].search([
                        ('kode_anggaran_id', '=', record.kode_anggaran_id.id),
                        ('rkap_id.branch_id', '=', record.kkhc_id.branch_id.id)
                    ])
                    rkap_lines._compute_realisasi()

        # self._validate_nominal_vs_pagu()

        return res

    def action_approve(self):
        """Metode untuk menyetujui catatan."""
        self.write({'approval_status': 'approved'})

    def action_reject(self):
        """Metode untuk menolak catatan."""
        self.write({'approval_status': 'rejected'})

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.deskripsi}"  # Atur format sesuai kebutuhan
            result.append((record.id, name))
        return result

    # @api.depends('nominal_pengajuan', 'nominal_disetujui')
    # def _compute_sisa_pengajuan(self):
    #     for line in self:
    #         line.sisa_pengajuan = line.nominal_pengajuan - line.nominal_disetujui

    def get_bank_accounts(self):
        penerimaan = {}
        pengeluaran = {}

        for line in self.lines:
            account_type = line.kode_anggaran_id.account_type
            if account_type == 'penerimaan':
                if line.bank_account_id not in penerimaan:
                    penerimaan[line.bank_account_id] = 0
                penerimaan[line.bank_account_id] += line.amount
            elif account_type == 'pengeluaran':
                if line.bank_account_id not in pengeluaran:
                    pengeluaran[line.bank_account_id] = 0
                pengeluaran[line.bank_account_id] += line.amount

        return {
            'penerimaan': penerimaan,
            'pengeluaran': pengeluaran,
        }

    @api.onchange('limit')
    def _onchange_limit(self):
        if self.limit:
            self.nominal_disetujui = self.limit
    
    def action_approval_kkhc(self):
        current_user = self.env.user

        current_date = fields.Date.context_today(self)
        line_approval = self.env['x_account_keuangan_kkhc_line_approval_line']

        for line in self.x_x_account_keuangan_kkhc_line_approval_line_ids.sorted('x_sequence'):
            if line.x_name != "approved":
                line_not_approve = line.search([
                    ('x_name', '=', None),
                    ('x_account_keuangan_kkhc_line_id', '=', self.id),
                ])

                if line_not_approve:
                    line_approval |= line_not_approve


        if line_approval:
            approval = line_approval[0]
            if approval:
                is_approved = False

                if approval.x_approver_user_id:
                    effective_approver = approval.x_approver_user_id
                    if effective_approver and effective_approver.user_id == current_user:
                        is_approved = True

                elif approval.x_approver_jabatan_id:
                    employees_with_position = self.env['hr.employee'].search([
                        ('keterangan_jabatan_id', '=', approval.x_approver_jabatan_id.id)
                    ])

                    effective_approvers = [(emp) for emp in employees_with_position]
                    if current_employee in effective_approvers:
                        is_approved = True

                elif approval.x_approver_ds_level:
                    ds_level = int(approval.x_approver_ds_level)
                    manager = approval.x_hr_leave_id.employee_id
                    for i in range(ds_level):
                        manager = manager.parent_id if manager else None

                    if manager:
                        effective_approver = manager
                        if effective_approver and effective_approver.user_id == current_user:
                            is_approved = True

                elif approval.x_approver_role_id:
                    role_users = self.env['res.users'].search([('groups_id', 'in', approval.x_approver_role_id.id)])
                    effective_approvers = [(user.employee_id) for user in role_users if user.employee_id]
                    if current_employee in effective_approvers:
                        is_approved = True


                if is_approved:
                    approval.write({'x_name': "approved", 'write_date': current_date})
                    
                    if all(line.x_name == "approved" for line in self.x_x_account_keuangan_kkhc_line_approval_line_ids):
                        # self.kkhc_id.action_confirm()
                        self.kkhc_id.kode_anggaran_id._reduce_saldo()

                        return {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _("Approval Successful"),
                                    'message': _('You have successfully approved this leave request.'),
                                    'type': 'success',
                                    'sticky': False,
                                }
                            }
                else:
                    raise ValidationError("Anda bukan approver yang sesuai untuk level persetujuan ini.")
