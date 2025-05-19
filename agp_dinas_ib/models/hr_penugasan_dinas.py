from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
import re
import math
import logging

_logger = logging.getLogger(__name__)


class HrLeaveDinas(models.Model):
    _name = "hr.leave.dinas"
    _description = "Module Dinas"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"

    name = fields.Char(string='Nomor', readonly=True, index="trigram", default=lambda self: _('New'))
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    nota_dinas_id = fields.Many2one('nota.dinas', string="Nota Dinas", domain=[('state', '=', 'done')])
    assigner_id = fields.Many2one('hr.employee', string="Pembuat Nota Dinas/Pemohon")
    assignee_id = fields.Many2one('hr.employee', string="Peserta")
    assignee_ids = fields.Many2many('hr.employee', 'hr_employee_assignee_ids_rel', 'leave_dinas_id', 'employee_id', string="Peserta Dinas")
    pemberi_undangan_id = fields.Many2one('hr.employee', string='Pemberi Undangan - archived')
    pemberi_undangan = fields.Text('Pemberi Undangan')
    is_pemberi_undangan = fields.Boolean(compute='_compute_is_pemberi_undangan')
    agenda_dinas = fields.Text('Maksud Perjalanan Dinas', compute="_compute_agenda_dinas", store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_gm_sppd_approval', 'Menunggu Approval SPPD oleh GM (Cabang)'),
        ('waiting_dirut_sppd_approval_from_gm', 'Menunggu Approval SPPD oleh Dirut (Cabang)'),
        ('sppd_approved_input_biaya', 'SPPD Disetujui, Input Biaya (Cabang)'),
        ('waiting_for_review_biaya', 'Menunggu Review Biaya'),
        ('review_biaya_done', 'Review Biaya Selesai'),
        ('running', 'Running'),
        ('pause', 'Pause'),
        ('done', 'Selesai'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', track_visibility='onchange')
    transport = fields.Selection([
        ('kendaraan_dinas', 'Kendaraan Dinas'),
        ('kendaraan_pribadi', 'Kendaraan Pribadi')
    ], string='Transport - archived', default='kendaraan_dinas')
    transport_ids = fields.Many2many('hr.sppd.transport', string='Transport')
    branch_id = fields.Many2one('res.branch', string="Tempat Berangkat")
    destination_place = fields.Char('Tempat Tujuan', compute="_compute_destination_place", store=True)
    date_from = fields.Date("Tanggal Berangkat")
    date_to = fields.Date("Tanggal Kembali")
    date_change_dest = fields.Date("Tanggal Pindah Tujuan")
    is_pindah_tujuan = fields.Boolean()
    facility = fields.Text("Fasilitas", default="Dengan Fasilitas Sebagaimana Terlampir")
    total_biaya_dinas = fields.Monetary(string="Total Biaya Dinas", compute='_compute_total_biaya_dinas',
                                        currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Mata Uang',
                                  default=lambda self: self.env.company.currency_id.id)
    biaya_peserta_ids = fields.One2many('hr.leave.dinas.biaya', 'leave_dinas_id', string='Biaya per Peserta')
    participant_ids = fields.Many2many('hr.employee', 'hr_employee_participant_ids_rel', 'leave_dinas_id', 'employee_id', string="Pengikut", compute="_compute_participant")
    external_follower_ids = fields.One2many(
        'hr.leave.dinas.external.follower',
        'leave_dinas_id',
        string='Pengikut Eksternal'
    )
    pengikut_eksternal = fields.Boolean(string='Pengikut Eksternal')
    biaya_external_follower_ids = fields.One2many(
        'hr.leave.dinas.external.follower.biaya',
        'leave_dinas_id',
        string='Biaya per Pengikut Eksternal'
    )
    attachment_ids = fields.Many2many('ir.attachment', 'hr_leave_dinas_ir_attachment_rel', 'hr_leave_dinas_id', 'attachment_id', string="Attachments")

    # ================================= #
    # approval fields perpanjangan hari #
    # ================================= #
    extend_date_to = fields.Date(string="Tanggal Kembali Baru (Extend)")
    extend_reason = fields.Text(string="Alasan Perpanjangan Hari Dinas")
    extend_state = fields.Selection([
        ('waiting_mb', 'Menunggu Persetujuan Manager Bidang'),
        ('waiting_kadiv', 'Menunggu Persetujuan Kadiv'),
        ('waiting_gm_cabang_extend', 'Menunggu Persetujuan GM Cabang'),
        ('waiting_dirop', 'Menunggu Persetujuan Direktur Operasional'),
        ('waiting_dirkeu', 'Menunggu Persetujuan Direktur Keuangan'),
        ('waiting_dirut', 'Menunggu Persetujuan Direktur Utama'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
        ('cancelled', 'Dibatalkan'),
    ], string="Status Perpanjangan", tracking=True)

    is_cabang_sppd = fields.Boolean(
        string="SPPD Kantor Cabang?",
        compute='_compute_is_cabang_sppd',
        store=True
    )

    extend_approval_ids = fields.One2many('hr.leave.dinas.extend.approval', 'leave_dinas_id',
                                          string="Approval Perpanjangan Hari")

    unexpected_cost_ids = fields.One2many(
        'hr.leave.dinas.unexpected.cost',
        'leave_dinas_id',
        string='Biaya Tak Terduga'
    )

    @api.constrains('date_from', 'date_to')
    def _check_tanggal_dinas(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("Tanggal kembali harus setelah tanggal berangkat."))

    @api.depends('nota_dinas_id')
    def _compute_destination_place(self):
        for rec in self:
            rec.destination_place = rec.nota_dinas_id.destination_place

    @api.depends('pemberi_undangan_id')
    def _compute_is_pemberi_undangan(self):
        for record in self:
            employee = self.env.user.employee_id
            record.is_pemberi_undangan = record.pemberi_undangan_id == employee

    @api.depends('nota_dinas_id')
    def _compute_agenda_dinas(self):
        for rec in self:
            rec.agenda_dinas = rec.nota_dinas_id.agenda_desc

    @api.depends('nota_dinas_id')
    def _compute_participant(self):
        self.mapped('nota_dinas_id.nota_dinas_line_ids')
        for rec in self:
            if rec.nota_dinas_id:
                part = rec.nota_dinas_id.nota_dinas_line_ids.mapped('applicant_id')
                rec.participant_ids = [(6, 0, part.ids[1:])] if part else [(6, 0, [])]
            else:
                rec.participant_ids = [(6, 0, [])]

    @api.depends('nota_dinas_id.type_nodin')
    def _compute_is_cabang_sppd(self):
        for rec in self:
            if rec.nota_dinas_id and rec.nota_dinas_id.type_nodin:
                rec.is_cabang_sppd = (rec.nota_dinas_id.type_nodin == 'kantor_cabang')
            else:
                rec.is_cabang_sppd = False

    def _get_multiplier_from_satuan(self, satuan, durasi_hari):
        satuan_original_case = satuan
        satuan = (satuan or '').lower().strip()

        # Daftar satuan yang dianggap fixed (multiplier selalu 1), lowercase
        # 'perjalanan' termasuk di sini karena multipliernya 1 (sekali perjalanan)
        fixed_rate_units_cleaned = ['rp', 'rupiah', 'paket', 'unit', 'buah', 'set', 'perjalanan']

        # Bersihkan inputan satuan untuk matching dengan fixed_rate_units_cleaned
        # Hanya huruf dan angka, spasi, lalu strip
        satuan_bersih_untuk_fixed_check = re.sub(r'[^a-z0-9\s]', '', satuan).strip()

        # LANGKAH 1: Cek apakah satuan adalah unit fixed yang eksplisit
        if satuan_bersih_untuk_fixed_check in fixed_rate_units_cleaned:
            # Jika "rp", "paket", "perjalanan" (setelah dibersihkan) ada di daftar fixed, multiplier = 1
            # Ini juga akan menangani "Rp / Perjalanan" karena "perjalanan" ada di fixed_rate_units_cleaned
            # dan "rp" juga, tapi "perjalanan" lebih spesifik.
            # Jika hanya "rp", maka akan match di sini.
            return 1

        # LANGKAH 2: Jika bukan unit fixed eksplisit, coba parsing unit waktu
        time_units = {
            'hari': 1,
            'minggu': 7,
            'bulan': 30,  # Asumsi standar
            'tahun': 365,  # Asumsi standar
        }

        # Coba cari pola seperti "1 hari", "7 minggu", "per hari", "harian"
        # Regex ini mencari (opsional angka) spasi (opsional) unit_waktu
        # \d* -> nol atau lebih digit (untuk angka seperti 7)
        # \s* -> nol atau lebih spasi
        # (hari|minggu|bulan|tahun) -> salah satu unit waktu

        # Lebih baik memisahkan pencarian keyword waktu karena regex bisa kompleks dengan variasi input

        # Coba dulu cari pola "angka unit_waktu"
        match_numeric_time = re.search(r'(\d+)\s*(hari|minggu|bulan|tahun)', satuan)
        if match_numeric_time:
            interval = int(match_numeric_time.group(1))
            unit = match_numeric_time.group(2)
            days_per_interval = interval * time_units.get(unit, 1)  # default 1 jika unit aneh (seharusnya tidak)
            return math.ceil(durasi_hari / days_per_interval) if days_per_interval > 0 else 1

        # Jika tidak ada angka, coba cari keyword unit waktu saja (misal "per hari", "harian")
        for unit_keyword, days_in_unit in time_units.items():
            if unit_keyword in satuan:  # Jika "hari" ada di dalam "rp / hari" atau "harian"
                # Jika "perjalanan" sudah dihandle di atas sebagai fixed, tidak akan masuk sini
                return math.ceil(durasi_hari / days_in_unit) if days_in_unit > 0 else 1

        # LANGKAH 3: Fallback jika tidak ada yang cocok
        # Jika satuan tidak mengandung keyword waktu yang dikenali DAN bukan unit fixed yang dikenali,
        # maka multipliernya 1 (dianggap sebagai biaya lumpsum/sekali).
        # Ini penting agar "Rp" yang lolos validasi di _check_valid_satuan dihitung benar.
        _logger.info(
            f"Satuan '{satuan_original_case}' tidak mengandung unit waktu yang dikenali atau bukan unit fixed eksplisit yang di-handle berbeda, multiplier dihitung sebagai 1.")
        return 1

    @api.depends('biaya_peserta_ids.amount_total',
                 'biaya_external_follower_ids.amount_total')
    def _compute_total_biaya_dinas(self):
        for rec in self:
            total_internal = sum(rec.biaya_peserta_ids.mapped('amount_total'))
            total_external = sum(rec.biaya_external_follower_ids.mapped('amount_total'))
            rec.total_biaya_dinas = total_internal + total_external

    def generate_sppd_sequence(self):
        angka_sequence = self.env['ir.sequence'].next_by_code('hr.leave.dinas')
        roman_months = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'}
        current_month = datetime.now().month
        current_month_roman = roman_months.get(current_month, 'I')
        tahun = datetime.now().year
        bulan = datetime.now().strftime('%m')
        full_sequence = f"SPD/{tahun}/{bulan}/{current_month_roman}/{angka_sequence}"
        return full_sequence

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.generate_sppd_sequence()
        if vals.get('nota_dinas_id'):
            nota_dinas = self.env['nota.dinas'].browse(vals['nota_dinas_id'])
            if nota_dinas:
                part_ids = nota_dinas.nota_dinas_line_ids.mapped('applicant_id.id')[1:]
                vals.update({'participant_ids': [(6, 0, part_ids)]})
        res = super(HrLeaveDinas, self).create(vals)
        for rec in res:
            rec.state = 'draft'
        # biaya peserta internal
        peserta_ids = [res.assigner_id.id] + res.participant_ids.ids
        for emp in peserta_ids:
            self.env['hr.leave.dinas.biaya'].create({
                'leave_dinas_id': res.id,
                'employee_id': emp,
            })
        # biaya peserta eksternal
        if res.pengikut_eksternal and res.external_follower_ids:
            vals_list_biaya_ext = []
            for follower in res.external_follower_ids:
                # Cek apakah sudah ada biaya untuk follower ini (mencegah duplikasi jika create dipanggil lagi)
                existing_biaya = self.env['hr.leave.dinas.external.follower.biaya'].search([
                    ('leave_dinas_id', '=', res.id),
                    ('external_follower_id', '=', follower.id)
                ], limit=1)
                if not existing_biaya:
                    vals_list_biaya_ext.append({
                        'leave_dinas_id': res.id,
                        'external_follower_id': follower.id,
                        # Bisa tambahkan default biaya_header_id jika ada logika default
                    })
            if vals_list_biaya_ext:
                self.env['hr.leave.dinas.external.follower.biaya'].create(vals_list_biaya_ext)
        return res

    def write(self, vals):
        res = super(HrLeaveDinas, self).write(vals)
        for sppd in self:
            if 'external_follower_ids' in vals or (vals.get('pengikut_eksternal') and sppd.external_follower_ids):
                # Jika ada perubahan pada daftar pengikut eksternal
                # atau checkbox pengikut eksternal diaktifkan dan sudah ada listnya
                sppd_external_followers = sppd.external_follower_ids
                existing_biaya_followers = sppd.biaya_external_follower_ids.mapped('external_follower_id')

                vals_list_biaya_ext = []
                for follower in sppd_external_followers:
                    if follower not in existing_biaya_followers:
                        vals_list_biaya_ext.append({
                            'leave_dinas_id': sppd.id,
                            'external_follower_id': follower.id,
                        })
                if vals_list_biaya_ext:
                    self.env['hr.leave.dinas.external.follower.biaya'].create(vals_list_biaya_ext)

                # Hapus biaya untuk pengikut eksternal yang sudah dihapus dari SPPD
                # Ini penting agar data biaya tetap sinkron
                followers_to_remove_biaya_for = existing_biaya_followers - sppd_external_followers
                if followers_to_remove_biaya_for:
                    biaya_to_unlink = sppd.biaya_external_follower_ids.filtered(
                        lambda b: b.external_follower_id in followers_to_remove_biaya_for
                    )
                    biaya_to_unlink.unlink()
        return res

    def _get_sppd_approvers(self, role_code):
        dept = self.env['hr.department'].search([('biaya_sppd_role', '=', role_code)], limit=1)
        return dept.penanggung_jawab_ids or dept.manager_id

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Hanya bisa submit jika status masih Draft.'))
            rec._compute_is_cabang_sppd()

            if rec.is_cabang_sppd:
                pemohon_sppd = rec.assigner_id
                if not pemohon_sppd or not pemohon_sppd.hr_branch_id:
                    raise UserError(_("Pemohon SPPD atau branch pemohon tidak valid."))

                gm_cabang_pemohon = pemohon_sppd.hr_branch_id.manager_id

                if pemohon_sppd == gm_cabang_pemohon and gm_cabang_pemohon:  # The applicant is the GM of the branch
                    rec.state = 'waiting_dirut_sppd_approval_from_gm'  # To the Dirut to approve SPPD
                    rec.message_post(body=_(
                        "SPPD Kantor Cabang diajukan oleh GM (%s) dan menunggu approval SPPD oleh Direktur Utama.") % pemohon_sppd.name)
                else:  # The applicant is an ordinary staff member at the Branch
                    rec.state = 'waiting_gm_sppd_approval'
                    rec.message_post(body=_("SPPD Kantor Cabang telah disubmit dan menunggu approval SPPD oleh GM."))
            else:  # Head Office or other type
                rec.state = 'waiting_for_review_biaya'
                rec.message_post(body=_("SPPD (Non-Cabang) telah disubmit dan menunggu review biaya."))

    def _cron_update_sppd_states(self):
        _logger.info("Cron SPPD Auto Update State: Starting job...")
        today = fields.Date.today()

        # Ambil SPPD yang statusnya masih berjalan atau sudah review biaya selesai
        # dan punya tanggal berangkat & kembali rencana awal
        sppds_to_check = self.search([
            ('state', 'in', ['review_biaya_done', 'running', 'pause']),
            # Tambahkan 'pause' jika deviasi bisa terjadi saat pause
            ('date_from', '!=', False),
            ('date_to', '!=', False)  # date_to di sini adalah tanggal kembali rencana awal SPPD
        ])

        _logger.info(f"Cron SPPD: Found {len(sppds_to_check)} SPPDs to check.")

        for sppd in sppds_to_check:
            _logger.info(
                f"Cron SPPD: Checking SPPD {sppd.name} (State: {sppd.state}, Date From: {sppd.date_from}, Date To Plan: {sppd.date_to})")
            # 1. Mengubah status dari 'review_biaya_done' ke 'running'
            # Logika ini bisa tetap sama: jika tanggal berangkat sudah tiba/lewat, ubah jadi running.
            if sppd.state == 'review_biaya_done' and sppd.date_from <= today:
                sppd.write({'state': 'running'})
                _logger.info(f"Cron SPPD: SPPD {sppd.name} changed state to 'running'.")

            # 2. Mengubah status ke 'done' jika semua peserta sudah selesai
            if sppd.state == 'running' or sppd.state == 'pause':  # Cek juga yang 'pause' kalau-kalau deviasi terjadi saat itu
                all_participants_finished = True  # Asumsi awal semua selesai

                # Cek peserta internal
                if sppd.biaya_peserta_ids:
                    for biaya_internal in sppd.biaya_peserta_ids:
                        # Gunakan 'effective_date_to' dari biaya peserta internal
                        # Pastikan field 'effective_date_to' sudah ada dan di-compute dengan benar di hr.leave.dinas.biaya
                        tgl_kembali_peserta = biaya_internal.effective_date_to

                        if not tgl_kembali_peserta:
                            # Jika ada peserta yang belum ada tanggal kembali efektifnya (misal, perpanjangan belum diapprove)
                            # SPPD belum bisa dianggap selesai total dari sisi peserta ini.
                            # Atau, jika tidak ada deviasi, 'effective_date_to' akan sama dengan sppd.date_to
                            # Untuk amannya, jika tidak ada tanggal efektif, anggap belum selesai dari sisi cron ini.
                            # Namun, jika tidak ada deviasi, effective_date_to akan mengambil dari sppd.date_to.
                            # Jika ada perpanjangan yang masih 'waiting_approval', effective_date_to juga akan sppd.date_to.
                            # Jadi, perlu dipastikan logic effective_date_to.
                            # Untuk cron, kita hanya cek apakah tanggal efektif sudah lewat.
                            all_participants_finished = False
                            _logger.debug(
                                f"Cron SPPD: SPPD {sppd.name}, Peserta Internal {biaya_internal.employee_id.name} - effective_date_to belum ada.")
                            break

                        if tgl_kembali_peserta > today:
                            all_participants_finished = False
                            _logger.debug(
                                f"Cron SPPD: SPPD {sppd.name}, Peserta Internal {biaya_internal.employee_id.name} - Tgl Kembali Efektif ({tgl_kembali_peserta}) > Hari Ini ({today}).")
                            break
                    if not all_participants_finished:  # Jika sudah ketahuan ada yg belum selesai dari internal
                        _logger.info(f"Cron SPPD: SPPD {sppd.name} - Tidak semua peserta internal selesai.")
                        continue  # Lanjut ke SPPD berikutnya
                else:
                    # Jika tidak ada peserta internal sama sekali (mungkin tidak valid, tapi handle)
                    # Anggap saja "selesai" dari sisi internal jika tidak ada data.
                    # Atau bisa juga dianggap belum selesai jika minimal harus ada 1 peserta.
                    # Untuk cron, jika tidak ada, berarti tidak ada yang perlu ditunggu dari internal.
                    pass

                # Cek pengikut eksternal (jika all_participants_finished masih True)
                if all_participants_finished and sppd.pengikut_eksternal and sppd.biaya_external_follower_ids:
                    for biaya_eksternal in sppd.biaya_external_follower_ids:
                        # Gunakan 'effective_date_to_external' atau nama field yang disamakan
                        tgl_kembali_peserta_ext = biaya_eksternal.effective_date_to  # Asumsi nama field sama 'effective_date_to'

                        if not tgl_kembali_peserta_ext:
                            all_participants_finished = False
                            _logger.debug(
                                f"Cron SPPD: SPPD {sppd.name}, Peserta Eksternal {biaya_eksternal.external_follower_id.name} - effective_date_to belum ada.")
                            break

                        if tgl_kembali_peserta_ext > today:
                            all_participants_finished = False
                            _logger.debug(
                                f"Cron SPPD: SPPD {sppd.name}, Peserta Eksternal {biaya_eksternal.external_follower_id.name} - Tgl Kembali Efektif ({tgl_kembali_peserta_ext}) > Hari Ini ({today}).")
                            break
                    if not all_participants_finished:
                        _logger.info(f"Cron SPPD: SPPD {sppd.name} - Tidak semua peserta eksternal selesai.")
                        continue  # Lanjut ke SPPD berikutnya

                # Jika tidak ada peserta internal maupun eksternal dengan biaya (kasus aneh),
                # SPPD mungkin bisa dianggap 'done' berdasarkan date_to aslinya.
                if not sppd.biaya_peserta_ids and not (sppd.pengikut_eksternal and sppd.biaya_external_follower_ids):
                    if sppd.date_to <= today:
                        _logger.info(
                            f"Cron SPPD: SPPD {sppd.name} tidak memiliki peserta dengan biaya, dianggap selesai berdasarkan date_to SPPD.")
                        sppd.write({'state': 'done'})
                    else:
                        all_participants_finished = False  # Masih menunggu date_to SPPD
                        _logger.info(
                            f"Cron SPPD: SPPD {sppd.name} tidak memiliki peserta, menunggu date_to SPPD ({sppd.date_to}).")

                # Jika semua peserta (internal dan eksternal yang ada) sudah melewati tanggal kembali efektifnya
                if all_participants_finished:
                    sppd.write({'state': 'done'})
                    _logger.info(
                        f"Cron SPPD: SPPD {sppd.name} changed state to 'done' karena semua peserta telah selesai.")
                else:
                    _logger.info(f"Cron SPPD: SPPD {sppd.name} belum selesai karena masih ada peserta aktif.")

        _logger.info("Cron SPPD Auto Update State: Job finished.")
        return True

    def action_check_extend_done(self):
        for rec in self:
            has_waiting = any(a.state == 'waiting' for a in rec.extend_approval_ids)
            all_approved = all(a.state == 'approved' for a in rec.extend_approval_ids)

            if not has_waiting and all_approved:
                rec.date_to = rec.extend_date_to
                rec.extend_state = 'approved'
                rec.state = 'running'
                rec.message_post(body=_(
                    "Perpanjangan hari dinas telah disetujui oleh seluruh pihak. Tanggal kembali diperbarui menjadi %s."
                ) % rec.date_to.strftime('%d-%m-%Y'))

                # Reset data perpanjangan
                rec.extend_date_to = False
                rec.extend_reason = False
                rec.extend_state = False

    def _get_expected_approver_employee_ids(self):
        emp = self.assigner_id
        if not emp or not emp.department_id:
            return []

        current_dept = emp.department_id.sudo()

        approvers = []
        if current_dept.department_type == 'bidang':
            if current_dept.manager_id:
                approvers.append(current_dept.manager_id.id)
            else:
                return []
            if current_dept.parent_id and current_dept.parent_id.manager_id:
                approvers.append(current_dept.parent_id.manager_id.id)
            else:
                return []
        elif current_dept.department_type == 'divisi':
            if current_dept.manager_id:
                approvers.append(current_dept.manager_id.id)
            else:
                return []

        return approvers

    def _check_sppd_direksi_permission(self, expected_role):
        """
        Helper method untuk mengecek apakah user saat ini memiliki role direksi tertentu
        berdasarkan keterangan_jabatan_id.nodin_workflow.
        Mirip dengan _check_direksi_permission di nota.dinas, tapi disesuaikan untuk SPPD jika perlu.
        Parameter expected_role: 'dirut', 'dirkeu', 'dirop'.
        """
        self.ensure_one()
        current_employee = self.env.user.employee_id
        if not current_employee:
            return False

        # Pastikan field 'keterangan_jabatan_id' ada di hr.employee
        if not hasattr(current_employee, 'keterangan_jabatan_id') or not current_employee.keterangan_jabatan_id:
            _logger.warning(
                "Field 'keterangan_jabatan_id' tidak ditemukan atau kosong pada employee %s (user: %s) untuk validasi direksi SPPD.",
                current_employee.name, self.env.user.login)
            return False

        keterangan_jabatan = current_employee.keterangan_jabatan_id

        # Pastikan field 'nodin_workflow' ada di model keterangan_jabatan_id
        if not hasattr(keterangan_jabatan, 'nodin_workflow'):
            _logger.warning(
                "Field 'nodin_workflow' tidak ditemukan pada model %s (Keterangan Jabatan ID: %s) untuk validasi direksi SPPD.",
                keterangan_jabatan._name, keterangan_jabatan.id)
            return False

        return keterangan_jabatan.nodin_workflow == expected_role

    def action_gm_approve_sppd(self):
        self.ensure_one()
        if not self.is_cabang_sppd or self.state != 'waiting_gm_sppd_approval':
            raise UserError(_("Aksi ini hanya valid untuk SPPD Kantor Cabang yang menunggu approval SPPD oleh GM."))

        # Approver Validation: GM of the SPPD applicant branch
        # Assume GM is the manager of hr.branch where the applicant (assigner_id) works.
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

        pemohon_branch = self.assigner_id.hr_branch_id
        if not pemohon_branch:
            raise UserError(_("Pemohon SPPD (%s) tidak terdaftar di kantor cabang manapun.") % (self.assigner_id.name))
        if pemohon_branch.location != 'branch_office':
            raise UserError(
                _("SPPD ini tidak teridentifikasi sebagai SPPD Kantor Cabang (Branch Office)."))

        branch_manager = pemohon_branch.manager_id
        if not branch_manager:
            raise UserError(_("General Manager untuk kantor cabang (%s) pemohon (%s) belum diatur di master Branch.")
                            % (pemohon_branch.name, self.assigner_id.name))

        if current_employee != branch_manager:
            raise UserError(_("Anda (%s) bukan General Manager (%s) yang ditugaskan untuk kantor cabang ini.")
                            % (current_employee.name, branch_manager.name))

        self.state = 'sppd_approved_input_biaya'
        self.message_post(body=_(
            "SPPD Kantor Cabang telah disetujui oleh General Manager (%s). Silakan input rincian biaya."
        ) % current_employee.name)

    def action_dirut_approve_sppd_from_gm(self):
        """
        Aksi untuk Direktur Utama menyetujui SPPD Kantor Cabang
        yang diajukan oleh GM Cabang itu sendiri.
        """
        self.ensure_one()

        # 1. Validasi Tipe SPPD dan State
        if not self.is_cabang_sppd or self.state != 'waiting_dirut_sppd_approval_from_gm':
            raise UserError(
                _("Aksi ini hanya valid untuk SPPD Kantor Cabang yang menunggu approval SPPD oleh Direktur Utama (diajukan GM)."))

        # 2. Validasi Pemohon adalah GM (opsional, karena state sudah menyiratkan)
        # pemohon_sppd = self.assigner_id
        # gm_cabang_pemohon = pemohon_sppd.hr_branch_id.manager_id if pemohon_sppd.hr_branch_id else False
        # if not (pemohon_sppd == gm_cabang_pemohon and gm_cabang_pemohon):
        #     raise UserError(_("SPPD ini tidak diajukan oleh GM Cabang yang sesuai."))

        # 3. Validasi Approver adalah Dirut
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

        if not self._check_sppd_direksi_permission('dirut'):
            raise UserError(
                _("Anda (%s) tidak memiliki wewenang sebagai Direktur Utama untuk menyetujui SPPD ini.") % current_employee.name)

        # 4. Lolos Validasi -> Ubah Status
        self.state = 'sppd_approved_input_biaya'
        self.message_post(body=_(
            "SPPD Kantor Cabang (diajukan GM) telah disetujui oleh Direktur Utama (%s). Silakan input rincian biaya."
        ) % current_employee.name)

    def action_submit_biaya_sppd(self):
        self.ensure_one()
        if not self.is_cabang_sppd or self.state != 'sppd_approved_input_biaya':
            raise UserError(
                _("Aksi ini hanya valid untuk SPPD Kantor Cabang yang sudah disetujui GM dan siap untuk submit biaya."))

        if not self.biaya_peserta_ids:
            raise UserError(
                _("Belum ada rincian biaya yang diinput untuk peserta manapun. Harap input biaya terlebih dahulu."))

        self.state = 'waiting_for_review_biaya'
        self.message_post(body=_(
            "Rincian biaya SPPD Kantor Cabang telah disubmit. Menunggu review & approval biaya oleh GM Cabang."
        ))


class HrLeaveDinasBiaya(models.Model):
    _name = 'hr.leave.dinas.biaya'
    _description = 'Biaya Per Peserta Dinas'

    leave_dinas_id = fields.Many2one('hr.leave.dinas', string='Referensi SPPD', ondelete='cascade')
    is_sppd_cabang = fields.Boolean(compute='_compute_is_sppd_cabang')
    employee_id = fields.Many2one('hr.employee', string='Peserta Dinas', required=True)
    biaya_header_id = fields.Many2one('hr.dinas.biaya.header', string='Template Biaya')
    amount_total = fields.Monetary(string='Total Biaya', compute='_compute_total_biaya', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Mata Uang',
                                  default=lambda self: self.env.company.currency_id.id)
    approval_mb_umum = fields.Boolean(string="Approved by MB Umum", default=False)
    approval_kadiv_sdm_umum = fields.Boolean(string="Approved by Kadiv SDM dan Umum", default=False)
    approval_mb_keuangan = fields.Boolean(string="Approved by MB Keuangan", default=False)
    approval_kadiv_keuangan = fields.Boolean(string="Approved by Kadiv Keuangan", default=False)
    approval_mb_keuangan_transfer_biaya = fields.Boolean(string="Menunggu Biaya ditransfer", default=False)
    approval_gm_cabang = fields.Boolean(string="Approved by GM Cabang", default=False)
    approval_stage = fields.Selection([
        ('draft', 'Draft'),
        # State untuk Cabang
        ('waiting_gm_biaya_cabang', 'Menunggu Approval Biaya GM Cabang'),
        # Bisa jadi 'draft' saja cukup jika _compute benar
        ('waiting_kadiv_keu_pusat_transfer', 'Menunggu Transfer Kadiv Keu. Pusat'),
        # State untuk Pusat (mungkin bisa direuse sebagian atau perlu nama beda)
        ('waiting_mb_umum', 'Menunggu Approval MB Umum (Pusat)'),  # Bisa jadi 'draft' saja cukup
        ('waiting_kadiv_sdm_umum', 'Menunggu Approval Kadiv SDM & Umum (Pusat)'),
        ('waiting_mb_keuangan_pusat', 'Menunggu Approval MB Keuangan (Pusat)'),
        ('waiting_kadiv_keuangan_pusat', 'Menunggu Approval Kadiv Keuangan (Pusat)'),
        # State Bersama
        ('waiting_for_transfer_biaya', 'Menunggu Biaya Ditransfer'),
        # Mungkin ini bisa jadi state setelah Kadiv Keu Pusat (Cabang) atau Kadiv Keu (Pusat)
        ('biaya_transfered', 'Biaya Ditransfer'),
        ('done', 'Selesai'),
    ], string="Tahap Approval Biaya", compute='_compute_approval_stage', store=True)
    approval_kadiv_keu_transfer_cabang = fields.Boolean(
        string="Approved/Transferred by Kadiv Keu. Pusat (Cabang)",
        default=False,
        copy=False
    )
    biaya_line_ids = fields.One2many('hr.leave.dinas.biaya.line', 'dinas_biaya_id', string='Rincian Biaya')
    # Field untuk semua jenis deviasi per peserta internal
    is_deviated = fields.Boolean(string="Ada Deviasi", default=False, copy=False)
    deviation_type = fields.Selection([
        ('early_return', 'Kembali Lebih Awal'),
        ('extend_days', 'Perpanjangan Hari Dinas'),
        ('change_location', 'Pindah Lokasi'),
    ], string='Jenis Deviasi', copy=False)

    # Field untuk masing-masing tipe deviasi
    deviated_date_to = fields.Date(string="Tgl Kembali Aktual (Deviasi)",
                                   copy=False)  # Untuk early_return & extend_days
    deviated_destination_place = fields.Char(string="Tujuan Aktual (Deviasi)", copy=False)  # Untuk change_location
    deviation_city_transfer_date = fields.Date(string="Tgl Efektif Pindah Tujuan (Deviasi)",
                                               copy=False)  # Untuk change_location
    deviation_reason = fields.Text(string="Alasan Deviasi", copy=False)

    # Field untuk alur approval perpanjangan per peserta (jika 'extend_days' dipilih)
    # Kita bisa buat model approval baru atau menggunakan/adaptasi hr.leave.dinas.extend.approval
    # Untuk sekarang, kita buat field state sederhana dulu, alur detail bisa menyusul.
    extend_deviation_state = fields.Selection([
        ('draft', 'Draft Deviasi'),  # Saat wizard deviasi perpanjangan di-submit
        ('waiting_approval', 'Menunggu Persetujuan Perpanjangan'),  # State umum, detail approver bisa di model lain
        ('approved', 'Perpanjangan Disetujui'),
        ('rejected', 'Perpanjangan Ditolak'),
    ], string="Status Deviasi Perpanjangan", default=False, copy=False, tracking=True)

    # One2many ke model approval deviasi (jika mau pakai alur berjenjang seperti extend_approval_ids sebelumnya)
    # Misalnya:
    # deviation_approval_ids = fields.One2many('hr.leave.dinas.biaya.deviation.approval', 'biaya_peserta_id', string="Approval Deviasi")

    # Untuk menampilkan tanggal kembali efektif peserta ini (bisa jadi dari deviasi atau SPPD utama)
    effective_date_to = fields.Date(string="Tgl Kembali Efektif Peserta", compute="_compute_effective_date_to",
                                    store=True)
    participant_extend_approval_ids = fields.One2many('hr.leave.dinas.participant.extend.approval','biaya_peserta_id')

    @api.depends('leave_dinas_id.nota_dinas_id.type_nodin')
    def _compute_is_sppd_cabang(self):
        for rec in self:
            sppd = rec.leave_dinas_id
            if sppd and sppd.nota_dinas_id:
                if sppd.nota_dinas_id.type_nodin == 'kantor_cabang':
                    rec.is_sppd_cabang = True
                else:
                    rec.is_sppd_cabang = False
            else:
                rec.is_sppd_cabang = False

    @api.onchange('biaya_header_id')
    def _onchange_biaya_header_id(self):
        for rec in self:
            if rec.biaya_header_id:
                rec.biaya_line_ids = [(5, 0, 0)] + [
                    (0, 0, {
                        'komponen_id': line.komponen_id.id,
                        'jenis_lokasi': line.jenis_lokasi,
                        'golongan': line.golongan,
                        'jumlah': line.jumlah,
                        'satuan': line.satuan,
                        'currency_id': line.currency_id.id,
                    }) for line in rec.biaya_header_id.biaya_line_ids
                ]

    @api.depends('biaya_line_ids.jumlah', 'biaya_line_ids.satuan',
                 'leave_dinas_id.date_from', 'effective_date_to')
    def _compute_total_biaya(self):
        for rec in self:
            total = 0
            durasi = 1
            if rec.leave_dinas_id.date_from and rec.leave_dinas_id.date_to:
                durasi = (rec.leave_dinas_id.date_to - rec.leave_dinas_id.date_from).days or 1

            for line in rec.biaya_line_ids:
                if line.komponen_id.is_laundry and durasi <= 1:
                    continue
                multiplier = rec.leave_dinas_id._get_multiplier_from_satuan(line.satuan, durasi)
                total += line.jumlah * multiplier

            rec.amount_total = total

    @api.depends(
        'is_sppd_cabang', 'approval_gm_cabang', 'approval_kadiv_keu_transfer_cabang',  # Cabang
        'approval_mb_umum', 'approval_kadiv_sdm_umum',  # Pusat
        'approval_mb_keuangan', 'approval_kadiv_keuangan',  # Mungkin bersama atau perlu flag cabang/pusat
        'approval_mb_keuangan_transfer_biaya'  # Mungkin bersama
    )
    def _compute_approval_stage(self):
        for rec in self:
            if rec.is_sppd_cabang:
                # --- ALUR CABANG ---
                if rec.approval_kadiv_keu_transfer_cabang:  # Jika sudah ditransfer/diapprove Kadiv Keu Pusat
                    # Apakah MB Keu Pusat juga melakukan transfer fisik? Atau Kadiv Keu ini sudah termasuk transfer?
                    # Kita asumsikan setelah Kadiv Keu. Pusat approve/transfer, langsung 'biaya_transfered'
                    rec.approval_stage = 'biaya_transfered'
                elif rec.approval_gm_cabang:
                    rec.approval_stage = 'waiting_kadiv_keu_pusat_transfer'
                else:
                    rec.approval_stage = 'draft'  # Atau 'waiting_gm_biaya_cabang'
            else:
                # --- ALUR PUSAT (EXISTING YANG PERLU DISESUAIKAN) ---
                if rec.approval_mb_keuangan_transfer_biaya:
                    rec.approval_stage = 'biaya_transfered'
                elif rec.approval_kadiv_keuangan:
                    # Jika MB Keu. Pusat juga transfer untuk Cabang, maka field approval_mb_keuangan_transfer_biaya bisa dipakai bersama
                    rec.approval_stage = 'waiting_for_transfer_biaya'  # Ini menunggu MB Keu untuk transfer
                elif rec.approval_mb_keuangan:
                    rec.approval_stage = 'waiting_kadiv_keuangan_pusat'  # State 'stage_4'
                elif rec.approval_kadiv_sdm_umum:
                    rec.approval_stage = 'waiting_mb_keuangan_pusat'  # State 'stage_3'
                elif rec.approval_mb_umum:
                    rec.approval_stage = 'waiting_kadiv_sdm_umum'  # State 'stage_2'
                else:
                    rec.approval_stage = 'draft'  # Atau 'waiting_mb_umum'

    def action_submit_to_mb_umum(self):
        for rec in self:
            rec.approval_stage = 'waiting_mb_umum'

    def action_approve_mb_umum(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))

        user_emp = self.env.user.employee_id

        # Validasi user harus penanggung jawab MB Umum
        mb_umum_dept = self.env['hr.department'].search([('department_type','=','bidang'),('biaya_sppd_role', '=', 'mb_umum')], limit=1)
        if not mb_umum_dept:
            raise ValidationError(_("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp not in mb_umum_dept.manager_id:
            raise UserError(_('Anda bukan Manager Bidang Umum.'))

        if self.approval_mb_umum:
            raise UserError(_('Biaya ini sudah disetujui oleh MB Umum.'))

        self.approval_mb_umum = True
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk peserta <b>%s</b> telah disetujui oleh MB Umum.") % (self.employee_id.name)
        )

    def action_approve_kadiv_sdm_umum(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))

        user_emp = self.env.user.employee_id

        kadiv_sdm_dept = self.env['hr.department'].search([
            ('department_type', '=', 'divisi'),
            ('biaya_sppd_role', '=', 'kadiv_sdm_umum')
        ], limit=1)
        if not kadiv_sdm_dept:
            raise ValidationError(_("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp != kadiv_sdm_dept.manager_id:
            raise UserError(_('Anda bukan Kadiv SDM dan Umum.'))

        if self.approval_kadiv_sdm_umum:
            raise UserError(_('Biaya ini sudah disetujui oleh Kadiv SDM dan Umum.'))

        self.approval_kadiv_sdm_umum = True
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk peserta <b>%s</b> telah disetujui oleh Kadiv SDM dan Umum.") % (self.employee_id.name)
        )

    def action_approve_mb_keuangan(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))

        user_emp = self.env.user.employee_id

        mb_keuangan_dept = self.env['hr.department'].search([
            ('department_type', '=', 'bidang'),
            ('biaya_sppd_role', '=', 'mb_keuangan')
        ], limit=1)
        if not mb_keuangan_dept:
            raise ValidationError(_("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp != mb_keuangan_dept.manager_id:
            raise UserError(_('Anda bukan MB Keuangan.'))

        if self.approval_mb_keuangan:
            raise UserError(_('Biaya ini sudah disetujui oleh MB Keuangan.'))

        self.approval_mb_keuangan = True
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk peserta <b>%s</b> telah disetujui oleh MB Keuangan.") % (self.employee_id.name)
        )

    def action_approve_kadiv_keuangan(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))

        user_emp = self.env.user.employee_id

        kadiv_keuangan_dept = self.env['hr.department'].search([
            ('department_type', '=', 'divisi'),
            ('biaya_sppd_role', '=', 'kadiv_keuangan')
        ], limit=1)
        if not kadiv_keuangan_dept:
            raise ValidationError(_("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp != kadiv_keuangan_dept.manager_id:
            raise UserError(_('Anda bukan Kadiv Keuangan.'))

        if self.approval_kadiv_keuangan:
            raise UserError(_('Biaya ini sudah disetujui oleh Kadiv Keuangan.'))

        self.approval_kadiv_keuangan = True
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk peserta <b>%s</b> telah disetujui oleh Kadiv Keuangan.") % (self.employee_id.name)
        )

    def action_transfer_biaya_mb_keuangan(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))

        user_emp = self.env.user.employee_id

        mb_keuangan_dept = self.env['hr.department'].search([
            ('department_type', '=', 'bidang'),
            ('biaya_sppd_role', '=', 'mb_keuangan')
        ], limit=1)
        if not mb_keuangan_dept:
            raise ValidationError(_("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp != mb_keuangan_dept.manager_id:
            raise UserError(_('Anda bukan MB Keuangan dan tidak berhak melakukan transfer biaya.'))

        if self.approval_mb_keuangan_transfer_biaya:
            raise UserError(_('Biaya sudah ditransfer oleh MB Keuangan.'))

        self.approval_mb_keuangan_transfer_biaya = True
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk peserta <b>%s</b> telah ditransfer oleh MB Keuangan.") % (self.employee_id.name)
        )

    def action_approve_gm_biaya_cabang(self):
        """Aksi untuk approval biaya oleh GM Cabang."""
        self.ensure_one()  # Pastikan hanya dijalankan untuk satu record biaya

        # 1. Validasi Tipe SPPD (harus Kantor Cabang)
        sppd = self.leave_dinas_id
        if not sppd.nota_dinas_id or sppd.nota_dinas_id.type_nodin != 'kantor_cabang':
            # Jika tidak ada Nota Dinas terkait atau tipenya bukan Cabang
            # Mungkin perlu fallback atau error spesifik jika SPPD bisa dibuat tanpa Nodin
            # Untuk saat ini, kita anggap SPPD Cabang selalu dari Nodin Cabang
            raise UserError(_("Approval GM Cabang hanya berlaku untuk SPPD dari Nota Dinas Kantor Cabang."))

        # 2. Validasi Status Awal (Harus dari Draft/Initial state)
        # Kita anggap 'draft' adalah state awal sebelum ada approval apapun
        # Nanti _compute_approval_stage perlu disesuaikan
        is_approved_pusat = self.approval_mb_umum or self.approval_kadiv_sdm_umum or \
                            self.approval_mb_keuangan or self.approval_kadiv_keuangan or \
                            self.approval_mb_keuangan_transfer_biaya
        if self.approval_gm_cabang or is_approved_pusat:
            raise UserError(_("Biaya ini sudah diproses atau bukan giliran approval GM Cabang."))

        # 3. Validasi Approver (GM Cabang)
        # Asumsi: GM Cabang adalah manager dari hr.branch tempat peserta (employee_id) bekerja
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

        # Cek branch peserta biaya ini
        peserta_branch = self.employee_id.hr_branch_id
        if not peserta_branch:
            raise UserError(_("Peserta (%s) tidak terdaftar di kantor cabang manapun.") % (self.employee_id.name))
        if peserta_branch.location != 'branch_office':
            # Safety check, harusnya tidak terjadi jika SPPD nya tipe Cabang
            raise UserError(
                _("Peserta (%s) tidak terdaftar di kantor cabang (Branch Office).") % (self.employee_id.name))

        branch_manager = peserta_branch.manager_id
        if not branch_manager:
            raise UserError(
                _("General Manager untuk kantor cabang (%s) belum diatur di master Branch.") % (peserta_branch.name))

        # Cek apakah user saat ini adalah GM Cabang yang dimaksud
        if current_employee != branch_manager:
            raise UserError(
                _("Anda (%s) bukan General Manager (%s) yang ditugaskan untuk kantor cabang peserta ini (%s).")
                % (current_employee.name, branch_manager.name, peserta_branch.name))

        # 4. Lolos Validasi -> Set Flag Approval
        self.approval_gm_cabang = True
        sppd.message_post(body=_(
            "Biaya untuk peserta <b>%s</b> telah disetujui oleh General Manager Cabang (%s)."
        ) % (self.employee_id.name, current_employee.name))

    def action_kadiv_keu_pusat_transfer_biaya_cabang(self):
        """
        Aksi untuk Kadiv Keuangan Kantor Pusat melakukan approval akhir dan/atau
        menandai biaya SPPD Kantor Cabang sebagai siap/sudah ditransfer.
        """
        self.ensure_one()

        # 1. Validasi Tipe SPPD (harus Kantor Cabang)
        if not self.is_sppd_cabang:  # Menggunakan field compute yang sudah ada
            raise UserError(_("Aksi ini hanya berlaku untuk biaya SPPD dari Kantor Cabang."))

        # 2. Validasi Status Sebelumnya
        #    Harus sudah diapprove oleh GM Cabang
        if not self.approval_gm_cabang:
            raise UserError(_("Biaya ini belum disetujui oleh GM Cabang."))
        #    Dan belum diproses oleh Kadiv Keu. Pusat sebelumnya
        if self.approval_kadiv_keu_transfer_cabang:
            raise UserError(_("Biaya ini sudah diproses oleh Kadiv Keuangan Kantor Pusat."))

        #    Opsional: Validasi berdasarkan approval_stage jika sudah diimplementasikan dengan benar
        #    if self.approval_stage != 'waiting_kadiv_keu_pusat_transfer':
        #        raise UserError(_("Biaya ini tidak dalam status menunggu approval/transfer Kadiv Keu. Pusat."))

        # 3. Validasi Approver adalah Kadiv Keuangan Kantor Pusat
        current_employee = self.env.user.employee_id
        if not current_employee:
            raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

        # Cari departemen Kadiv Keuangan Kantor Pusat
        # Asumsi hr.department punya field 'branch_id' (Many2one ke hr.branch)
        kadiv_keu_dept_pusat = self.env['hr.department'].search([
            ('biaya_sppd_role', '=', 'kadiv_keuangan'),  # Role yang sudah ada
            ('department_type', '=', 'divisi'),  # Sesuai instruksi loe
            ('branch_id.location', '=', 'head_office')  # Harus dari Head Office
        ], limit=1)

        if not kadiv_keu_dept_pusat:
            raise UserError(
                _("Tidak ditemukan konfigurasi Departemen Divisi di Kantor Pusat untuk role 'Kadiv Keuangan'. Harap hubungi Administrator."))

        approver_kadiv_keu_pusat = kadiv_keu_dept_pusat.manager_id
        if not approver_kadiv_keu_pusat:
            raise UserError(_("Manager untuk Departemen %s (role Kadiv Keuangan - Pusat) belum diatur.")
                            % (kadiv_keu_dept_pusat.name))

        if current_employee != approver_kadiv_keu_pusat:
            raise UserError(
                _("Anda (%s) bukan Kadiv Keuangan Kantor Pusat (%s) yang berwenang untuk aksi ini.")
                % (current_employee.name, approver_kadiv_keu_pusat.name))

        # 4. Lolos Validasi -> Set Flag Approval/Transfer
        self.approval_kadiv_keu_transfer_cabang = True
        self.leave_dinas_id.message_post(body=_(
            "Biaya untuk peserta <b>%s</b> (SPPD Cabang) telah disetujui/diproses transfer oleh Kadiv Keuangan Kantor Pusat (%s)."
        ) % (self.employee_id.name, current_employee.name))

    def action_mark_biaya_done(self):
        self.ensure_one()
        if self.approval_stage != 'biaya_transfered':
            raise UserError(_('Biaya ini belum mencapai tahap transfer.'))

        self.approval_stage = 'done'

        # Pastikan approval stage semua data biaya peserta sudah done untuk trigger status SPPD menjadi review_biaya_done
        all_done = all(
            biaya.approval_stage in ['done']
            for biaya in self.leave_dinas_id.biaya_peserta_ids
        )
        if all_done:
            self.leave_dinas_id.state = 'review_biaya_done'
            self.leave_dinas_id.message_post(
                body=_("Seluruh biaya peserta telah selesai di-review.")
            )

    @api.depends('leave_dinas_id.date_to',  # Tanggal rencana awal SPPD
                 'is_deviated', 'deviation_type',
                 'deviated_date_to',  # Hasil dari early_return atau extend_days yang sudah approved
                 'extend_deviation_state')
    def _compute_effective_date_to(self):
        for rec in self:
            sppd_original_date_to = rec.leave_dinas_id.date_to if rec.leave_dinas_id else False

            if rec.is_deviated and rec.deviated_date_to:
                # Jika ada deviasi tanggal kembali yang sudah tercatat di deviated_actual_date_to
                # (Ini diisi oleh wizard untuk early_return, atau oleh alur approval perpanjangan)
                rec.effective_date_to = rec.deviated_actual_date_to
            else:
                # Jika tidak ada deviasi tanggal kembali yang tercatat, gunakan tanggal SPPD asli
                rec.effective_date_to = sppd_original_date_to


class HrLeaveDinasBiayaLine(models.Model):
    _name = 'hr.leave.dinas.biaya.line'
    _description = 'Rincian Biaya Per Peserta Dinas'

    dinas_biaya_id = fields.Many2one('hr.leave.dinas.biaya', string='Referensi Biaya Peserta', ondelete='cascade')
    komponen_id = fields.Many2one('dinas.komponen', string='Komponen')
    jenis_lokasi = fields.Selection([
        ('ibu_kota', 'Ibu Kota Provinsi'),
        ('non_ibu_kota', 'Non Ibu Kota Provinsi'),
    ])
    golongan = fields.Selection([
        ('direksi', 'Dewan Komisaris / Direksi'),
        ('ks', 'KS/KDIV/VP/Setingkat/GM'),
        ('manager_bidang', 'Manager Bidang'),
        ('manager_sub', 'Manager Sub Bidang / Manager Unit'),
        ('staf', 'Staf'),
    ])
    jumlah = fields.Monetary(string='Jumlah (Rp)')
    satuan = fields.Char(string='Satuan',
                         help='Format satuan biaya. Contoh yang valid: "Rp / Hari", "Rp / 7 Hari", "Rp / 3 Bulan", atau "Rp / Perjalanan".')
    currency_id = fields.Many2one('res.currency', string='Mata Uang', default=lambda self: self.env.company.currency_id.id)

    @api.constrains('satuan')
    def _check_valid_satuan(self):
        allowed_time_keywords = ['hari', 'minggu', 'bulan', 'tahun', 'perjalanan']
        # Daftar satuan fixed yang diizinkan (dalam bentuk lowercase dan sudah dibersihkan dari simbol)
        # 'perjalanan' juga bisa dianggap fixed dari segi multiplier, tapi di sini untuk validasi keyword
        allowed_fixed_units_cleaned = ['rp', 'rupiah', 'paket', 'unit', 'buah', 'set']  # Sesuaikan daftar ini

        for rec in self:
            if rec.satuan:
                satuan_input_lower = rec.satuan.lower().strip()

                # Bersihkan satuan input untuk matching keyword (hanya huruf, angka, spasi)
                # Hati-hati jika "/" penting untuk format, tapi untuk keyword matching ini oke
                satuan_bersih_untuk_keyword = re.sub(r'[^a-z0-9\s]', '', satuan_input_lower).strip()

                contains_time_or_perjalanan_keyword = any(
                    kw in satuan_bersih_untuk_keyword for kw in allowed_time_keywords)

                # Cek apakah satuan yang sudah dibersihkan itu persis salah satu dari unit fixed yang diizinkan
                is_explicitly_allowed_fixed_unit = satuan_bersih_untuk_keyword in allowed_fixed_units_cleaned

                if not (contains_time_or_perjalanan_keyword or is_explicitly_allowed_fixed_unit):
                    # Jika tidak mengandung keyword waktu/perjalanan DAN BUKAN unit fixed yang secara eksplisit diizinkan
                    raise UserError(_(
                        "Satuan '%s' pada komponen '%s' tidak dikenali.\n"
                        "Gunakan format dengan periode (Contoh: 'Rp / Hari', 'Rp / Perjalanan') atau satuan tunggal yang valid (Contoh: 'Rp', 'Paket')."
                    ) % (rec.satuan, rec.komponen_id.name if rec.komponen_id else 'Tanpa Nama'))


class HrLeaveDinasExternalFollowerBiaya(models.Model):
    _name = 'hr.leave.dinas.external.follower.biaya'
    _description = 'Biaya Per Pengikut Eksternal Dinas'

    leave_dinas_id = fields.Many2one(
        'hr.leave.dinas',
        string='Referensi SPPD',
        ondelete='cascade',
        required=True,
        index=True
    )
    external_follower_id = fields.Many2one(
        'hr.leave.dinas.external.follower',
        string='Pengikut Eksternal',
        required=True,
        ondelete='cascade',
        index=True
    )
    name = fields.Char(related='external_follower_id.name', string="Nama Pengikut", readonly=True, store=True) # Untuk kemudahan display
    biaya_header_id = fields.Many2one('hr.dinas.biaya.header', string='Template Biaya')
    amount_total = fields.Monetary(
        string='Total Biaya',
        compute='_compute_total_biaya_external',
        currency_field='currency_id',
        store=True # Sebaiknya store=True jika akan sering diakses atau untuk performa
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        default=lambda self: self.env.company.currency_id.id,
        required=True
    )
    biaya_line_external_ids = fields.One2many(
        'hr.leave.dinas.external.follower.biaya.line',
        'external_dinas_biaya_id',
        string='Rincian Biaya Pengikut Eksternal',
        copy=True # Agar bisa di-copy saat SPPD di-duplicate
    )
    # Untuk approval & stage, kita samakan dulu fieldnya dengan hr.leave.dinas.biaya
    # Jika nanti ada perbedaan, bisa di-override atau dibuat field baru
    approval_mb_umum = fields.Boolean(string="Approved by MB Umum", default=False, copy=False)
    approval_kadiv_sdm_umum = fields.Boolean(string="Approved by Kadiv SDM dan Umum", default=False, copy=False)
    approval_mb_keuangan = fields.Boolean(string="Approved by MB Keuangan", default=False, copy=False)
    approval_kadiv_keuangan = fields.Boolean(string="Approved by Kadiv Keuangan", default=False, copy=False)
    approval_mb_keuangan_transfer_biaya = fields.Boolean(string="Menunggu Biaya ditransfer", default=False, copy=False)
    approval_gm_cabang = fields.Boolean(string="Approved by GM Cabang", default=False, copy=False)
    approval_kadiv_keu_transfer_cabang = fields.Boolean(
        string="Approved/Transferred by Kadiv Keu. Pusat (Cabang)",
        default=False,
        copy=False
    )
    is_sppd_cabang = fields.Boolean(related='leave_dinas_id.is_cabang_sppd', store=True) # Ambil dari SPPD utama
    approval_stage = fields.Selection([ # Samakan dulu dengan hr.leave.dinas.biaya
        ('draft', 'Draft'),
        ('waiting_gm_biaya_cabang', 'Menunggu Approval Biaya GM Cabang'),
        ('waiting_kadiv_keu_pusat_transfer', 'Menunggu Transfer Kadiv Keu. Pusat'),
        ('waiting_mb_umum', 'Menunggu Approval MB Umum (Pusat)'),
        ('waiting_kadiv_sdm_umum', 'Menunggu Approval Kadiv SDM & Umum (Pusat)'),
        ('waiting_mb_keuangan_pusat', 'Menunggu Approval MB Keuangan (Pusat)'),
        ('waiting_kadiv_keuangan_pusat', 'Menunggu Approval Kadiv Keuangan (Pusat)'),
        ('waiting_for_transfer_biaya', 'Menunggu Biaya Ditransfer'),
        ('biaya_transfered', 'Biaya Ditransfer'),
        ('done', 'Selesai'),
    ], string="Tahap Approval Biaya", compute='_compute_approval_stage_external', store=True, copy=False)
    # Field untuk semua jenis deviasi per peserta eksternal (BUKAN RELATED LAGI)
    is_deviated = fields.Boolean(string="Ada Deviasi", default=False, copy=False)
    deviation_type = fields.Selection([
        ('early_return', 'Kembali Lebih Awal'),
        ('extend_days', 'Perpanjangan Hari Dinas'),
        ('change_location', 'Pindah Lokasi'),
    ], string='Jenis Deviasi', copy=False)

    deviated_date_to = fields.Date(string="Tgl Kembali Aktual (Deviasi)", copy=False)
    deviated_destination_place = fields.Char(string="Tujuan Aktual (Deviasi)", copy=False)
    deviation_city_transfer_date = fields.Date(string="Tgl Efektif Pindah Tujuan (Deviasi)", copy=False)
    deviation_reason = fields.Text(string="Alasan Deviasi", copy=False)

    extend_deviation_state = fields.Selection([
        ('draft', 'Draft Deviasi'),
        ('waiting_approval', 'Menunggu Persetujuan Perpanjangan'),
        ('approved', 'Perpanjangan Disetujui'),
        ('rejected', 'Perpanjangan Ditolak'),
    ], string="Status Deviasi Perpanjangan", default=False, copy=False, tracking=True)

    # effective_date_to_external juga jadi compute biasa, tidak related
    effective_date_to = fields.Date(string="Tgl Kembali Efektif Peserta",
                                    compute="_compute_effective_date_to_external",  # Method compute-nya sendiri
                                    store=True)
    participant_extend_approval_ids = fields.One2many('hr.leave.dinas.participant.extend.approval', 'biaya_external_id')

    # ... (sisa field approval_mb_umum, dll. tetap field biasa, bukan related) ...
    # ... (method _compute_total_biaya_external, _onchange_biaya_header_id_external, _compute_approval_stage_external) ...

    @api.depends('leave_dinas_id.date_to',  # Tanggal rencana awal SPPD
                 'is_deviated', 'deviation_type',
                 'deviated_date_to',  # Hasil dari early_return atau extend_days yang sudah approved
                 'extend_deviation_state')
    def _compute_effective_date_to(self):
        for rec in self:
            sppd_original_date_to = rec.leave_dinas_id.date_to if rec.leave_dinas_id else False

            if rec.is_deviated and rec.deviated_actual_date_to:
                # Jika ada deviasi tanggal kembali yang sudah tercatat di deviated_actual_date_to
                # (Ini diisi oleh wizard untuk early_return, atau oleh alur approval perpanjangan)
                rec.effective_date_to = rec.deviated_actual_date_to
            else:
                # Jika tidak ada deviasi tanggal kembali yang tercatat, gunakan tanggal SPPD asli
                rec.effective_date_to = sppd_original_date_to

    api.depends('biaya_line_external_ids.jumlah', 'biaya_line_external_ids.satuan',
                'leave_dinas_id.date_from', 'leave_dinas_id.date_to')  # <<< PERBAIKAN DI SINI
    def _compute_total_biaya_external(self):
        for rec in self:
            total = 0
            sppd_utama = rec.leave_dinas_id
            durasi = 1
            if sppd_utama and sppd_utama.date_from and sppd_utama.date_to:
                durasi = (sppd_utama.date_to - sppd_utama.date_from).days + 1  # inklusif
                durasi = durasi if durasi > 0 else 1

            for line in rec.biaya_line_external_ids:  # Di sini sudah benar
                if line.komponen_id and line.komponen_id.is_laundry and durasi <= 1:
                    continue
                multiplier = 1
                if sppd_utama:
                    multiplier = sppd_utama._get_multiplier_from_satuan(line.satuan, durasi)
                total += line.jumlah * multiplier
            rec.amount_total = total

    @api.onchange('biaya_header_id')
    def _onchange_biaya_header_id_external(self):
        if self.biaya_header_id:
            self.biaya_line_external_ids = [(5, 0, 0)]
            new_lines_vals = []
            for line_template in self.biaya_header_id.biaya_line_ids:
                new_lines_vals.append({
                    'komponen_id': line_template.komponen_id.id,
                    'jenis_lokasi': line_template.jenis_lokasi,
                    'golongan': line_template.golongan, # Dibiarkan sama dulu
                    'jumlah': line_template.jumlah,
                    'satuan': line_template.satuan,
                    'currency_id': line_template.currency_id.id,
                })
            # Menggunakan create agar bisa di-trigger per line jika ada onchange di line
            self.biaya_line_external_ids = [(0, 0, vals) for vals in new_lines_vals]
        else:
            self.biaya_line_external_ids = [(5, 0, 0)]

    @api.depends( # Samakan dulu dengan hr.leave.dinas.biaya, nanti bisa disesuaikan
        'is_sppd_cabang', 'approval_gm_cabang', 'approval_kadiv_keu_transfer_cabang',
        'approval_mb_umum', 'approval_kadiv_sdm_umum',
        'approval_mb_keuangan', 'approval_kadiv_keuangan',
        'approval_mb_keuangan_transfer_biaya'
    )
    def _compute_approval_stage_external(self):
        # Salin logika dari _compute_approval_stage di hr.leave.dinas.biaya
        # Atau buat logika approval yang lebih sederhana jika untuk eksternal tidak serumit internal
        for rec in self:
            # Untuk sementara, kita buat simpel dulu, bisa disesuaikan nanti
            if rec.is_sppd_cabang:
                if rec.approval_kadiv_keu_transfer_cabang:
                    rec.approval_stage = 'biaya_transfered'
                elif rec.approval_gm_cabang:
                    rec.approval_stage = 'waiting_kadiv_keu_pusat_transfer'
                else:
                    rec.approval_stage = 'draft'
            else: # Alur Pusat (asumsi sama)
                if rec.approval_mb_keuangan_transfer_biaya:
                    rec.approval_stage = 'biaya_transfered'
                elif rec.approval_kadiv_keuangan:
                    rec.approval_stage = 'waiting_for_transfer_biaya'
                elif rec.approval_mb_keuangan:
                    rec.approval_stage = 'waiting_kadiv_keuangan_pusat'
                elif rec.approval_kadiv_sdm_umum:
                    rec.approval_stage = 'waiting_mb_keuangan_pusat'
                elif rec.approval_mb_umum:
                    rec.approval_stage = 'waiting_kadiv_sdm_umum'
                else:
                    rec.approval_stage = 'draft'

    def action_approve_gm_biaya_cabang_external(self):
        self.ensure_one()
        sppd = self.leave_dinas_id

        if not sppd.is_cabang_sppd:  # Menggunakan field compute dari SPPD utama
            raise UserError(_("Approval GM Cabang hanya berlaku untuk SPPD dari Kantor Cabang."))

        # Validasi status awal (misalnya harus dari 'draft' atau 'waiting_gm_biaya_cabang')
        # Lo bisa samakan dengan validasi di action_approve_gm_biaya_cabang internal
        if self.approval_gm_cabang or self.approval_stage not in ['draft', 'waiting_gm_biaya_cabang']:
            raise UserError(
                _("Biaya untuk pengikut eksternal %s sudah diproses atau bukan giliran approval GM Cabang.") % self.name)

        current_employee = self.env.user.employee_id
        if not current_employee:
            raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

        pemohon_sppd = sppd.assigner_id
        if not pemohon_sppd or not pemohon_sppd.hr_branch_id:
            raise UserError(_("Pemohon SPPD (%s) atau data kantor cabangnya tidak valid.") % (
                pemohon_sppd.name if pemohon_sppd else 'N/A'))

        branch_manager_pemohon = pemohon_sppd.hr_branch_id.manager_id
        if not branch_manager_pemohon:
            raise UserError(
                _("General Manager untuk kantor cabang pemohon SPPD (%s) belum diatur.") % (
                    pemohon_sppd.hr_branch_id.name))

        if current_employee != branch_manager_pemohon:
            raise UserError(
                _("Anda (%s) bukan General Manager (%s) dari kantor cabang pemohon SPPD (%s) yang berwenang.")
                % (current_employee.name, branch_manager_pemohon.name, pemohon_sppd.hr_branch_id.name))

        self.write({'approval_gm_cabang': True})  # Gunakan write untuk trigger recompute jika perlu

        sppd.message_post(body=_(
            "Biaya untuk pengikut eksternal <b>%s</b> telah disetujui oleh General Manager Cabang (%s)."
        ) % (self.name or self.external_follower_id.name,
             current_employee.name))  # Ambil nama dari field 'name' jika sudah ada

        # self._compute_approval_stage_external() # Recompute stage, atau biarkan Odoo yang handle via store=True
        return True  # Atau return action jika mau refresh/redirect

    # --- Tambahkan method-method action approval lainnya untuk Eksternal di sini ---
    # Contoh: action_kadiv_keu_pusat_transfer_biaya_cabang_external, dst.
    # dengan logika yang diadaptasi dari HrLeaveDinasBiaya

    def action_kadiv_keu_pusat_transfer_biaya_cabang_external(self):
        self.ensure_one()
        sppd = self.leave_dinas_id
        if not self.is_sppd_cabang:
            raise UserError(_("Aksi ini hanya berlaku untuk biaya SPPD dari Kantor Cabang."))
        if not self.approval_gm_cabang:
            raise UserError(_("Biaya ini belum disetujui oleh GM Cabang."))
        if self.approval_kadiv_keu_transfer_cabang:
            raise UserError(_("Biaya ini sudah diproses oleh Kadiv Keuangan Kantor Pusat."))
        if self.approval_stage != 'waiting_kadiv_keu_pusat_transfer':
            raise UserError(_("Biaya ini tidak dalam status menunggu approval/transfer Kadiv Keu. Pusat."))

        current_employee = self.env.user.employee_id
        if not current_employee:
            raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

        kadiv_keu_dept_pusat = self.env['hr.department'].search([
            ('biaya_sppd_role', '=', 'kadiv_keuangan'),
            ('department_type', '=', 'divisi'),
            ('branch_id.location', '=', 'head_office')
        ], limit=1)
        if not kadiv_keu_dept_pusat:
            raise UserError(
                _("Tidak ditemukan konfigurasi Departemen Divisi di Kantor Pusat untuk role 'Kadiv Keuangan'. Harap hubungi Administrator."))
        approver_kadiv_keu_pusat = kadiv_keu_dept_pusat.manager_id
        if not approver_kadiv_keu_pusat:
            raise UserError(_("Manager untuk Departemen %s (role Kadiv Keuangan - Pusat) belum diatur.")
                            % (kadiv_keu_dept_pusat.name))
        if current_employee != approver_kadiv_keu_pusat:
            raise UserError(
                _("Anda (%s) bukan Kadiv Keuangan Kantor Pusat (%s) yang berwenang untuk aksi ini.")
                % (current_employee.name, approver_kadiv_keu_pusat.name))

        self.write({'approval_kadiv_keu_transfer_cabang': True})
        sppd.message_post(body=_(
            "Biaya untuk pengikut eksternal <b>%s</b> (SPPD Cabang) telah disetujui/diproses transfer oleh Kadiv Keuangan Kantor Pusat (%s)."
        ) % (self.name or self.external_follower_id.name, current_employee.name))
        return True

    def action_submit_to_mb_umum_external(self):
        self.write({'approval_stage': 'waiting_mb_umum'})  # Ini mungkin lebih baik dihandle oleh compute stage
        # Atau jika ada validasi sebelum submit ke MB Umum, lakukan di sini
        self.leave_dinas_id.message_post(body=_("Biaya pengikut eksternal %s disubmit ke MB Umum.") % self.name)
        return True

    def action_approve_mb_umum_external(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))
        user_emp = self.env.user.employee_id
        mb_umum_dept = self.env['hr.department'].search(
            [('department_type', '=', 'bidang'), ('biaya_sppd_role', '=', 'mb_umum')], limit=1)
        if not mb_umum_dept:
            raise ValidationError(
                _("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        # Penanggung jawab bisa lebih dari satu, jadi pakai 'in'
        if user_emp not in mb_umum_dept.manager_id and user_emp not in mb_umum_dept.penanggung_jawab_ids:
            raise UserError(_('Anda bukan Manager Bidang Umum atau Penanggung Jawab yang ditunjuk.'))
        if self.approval_mb_umum:
            raise UserError(_('Biaya ini sudah disetujui oleh MB Umum.'))
        self.write({'approval_mb_umum': True})
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk pengikut eksternal <b>%s</b> telah disetujui oleh MB Umum.") % (
                        self.name or self.external_follower_id.name)
        )
        return True

    def action_approve_kadiv_sdm_umum_external(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))
        user_emp = self.env.user.employee_id
        kadiv_sdm_dept = self.env['hr.department'].search([
            ('department_type', '=', 'divisi'),
            ('biaya_sppd_role', '=', 'kadiv_sdm_umum')
        ], limit=1)
        if not kadiv_sdm_dept:
            raise ValidationError(
                _("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp != kadiv_sdm_dept.manager_id:  # Asumsi Kadiv hanya 1 (manager)
            raise UserError(_('Anda bukan Kadiv SDM dan Umum.'))
        if self.approval_kadiv_sdm_umum:
            raise UserError(_('Biaya ini sudah disetujui oleh Kadiv SDM dan Umum.'))
        self.write({'approval_kadiv_sdm_umum': True})
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk pengikut eksternal <b>%s</b> telah disetujui oleh Kadiv SDM dan Umum.") % (
                        self.name or self.external_follower_id.name)
        )
        return True

    def action_approve_mb_keuangan_external(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))
        user_emp = self.env.user.employee_id
        mb_keuangan_dept = self.env['hr.department'].search([
            ('department_type', '=', 'bidang'),
            ('biaya_sppd_role', '=', 'mb_keuangan')
        ], limit=1)
        if not mb_keuangan_dept:
            raise ValidationError(
                _("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp not in mb_keuangan_dept.manager_id and user_emp not in mb_keuangan_dept.penanggung_jawab_ids:
            raise UserError(_('Anda bukan MB Keuangan atau Penanggung Jawab yang ditunjuk.'))
        if self.approval_mb_keuangan:
            raise UserError(_('Biaya ini sudah disetujui oleh MB Keuangan.'))
        self.write({'approval_mb_keuangan': True})
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk pengikut eksternal <b>%s</b> telah disetujui oleh MB Keuangan.") % (
                        self.name or self.external_follower_id.name)
        )
        return True

    def action_approve_kadiv_keuangan_external(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))
        user_emp = self.env.user.employee_id
        kadiv_keuangan_dept = self.env['hr.department'].search([
            ('department_type', '=', 'divisi'),
            ('biaya_sppd_role', '=', 'kadiv_keuangan')
        ], limit=1)
        if not kadiv_keuangan_dept:
            raise ValidationError(
                _("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp != kadiv_keuangan_dept.manager_id:  # Asumsi Kadiv hanya 1 (manager)
            raise UserError(_('Anda bukan Kadiv Keuangan.'))
        if self.approval_kadiv_keuangan:
            raise UserError(_('Biaya ini sudah disetujui oleh Kadiv Keuangan.'))
        self.write({'approval_kadiv_keuangan': True})
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk pengikut eksternal <b>%s</b> telah disetujui oleh Kadiv Keuangan.") % (
                        self.name or self.external_follower_id.name)
        )
        return True

    def action_transfer_biaya_mb_keuangan_external(self):
        self.ensure_one()
        if self.is_sppd_cabang:
            raise UserError(_("Aksi ini tidak berlaku untuk SPPD Kantor Cabang."))
        user_emp = self.env.user.employee_id
        mb_keuangan_dept = self.env['hr.department'].search([
            ('department_type', '=', 'bidang'),
            ('biaya_sppd_role', '=', 'mb_keuangan')
        ], limit=1)
        if not mb_keuangan_dept:
            raise ValidationError(
                _("Tidak ditemukan konfigurasi department yang sesuai. Silahkan hubungi Administrator."))
        if user_emp not in mb_keuangan_dept.manager_id and user_emp not in mb_keuangan_dept.penanggung_jawab_ids:
            raise UserError(
                _('Anda bukan MB Keuangan atau Penanggung Jawab yang ditunjuk dan tidak berhak melakukan transfer biaya.'))
        if self.approval_mb_keuangan_transfer_biaya:
            raise UserError(_('Biaya sudah ditransfer oleh MB Keuangan.'))
        self.write({'approval_mb_keuangan_transfer_biaya': True})
        self.leave_dinas_id.message_post(
            body=_("Biaya untuk pengikut eksternal <b>%s</b> telah ditransfer oleh MB Keuangan.") % (
                        self.name or self.external_follower_id.name)
        )
        return True

    def action_mark_biaya_done_external(self):
        self.ensure_one()
        if self.approval_stage != 'biaya_transfered':
            raise UserError(_('Biaya ini belum mencapai tahap transfer.'))
        self.write({'approval_stage': 'done'})
        # Cek apakah semua biaya (internal & eksternal) sudah done untuk update SPPD utama
        self.leave_dinas_id._check_all_biaya_done()
        return True

    # --- Modifikasi di HrLeaveDinas ---
    # Tambahkan method untuk mengecek semua biaya
    # Di dalam class HrLeaveDinas(models.Model):
    def _check_all_biaya_done(self):
        self.ensure_one()
        all_internal_done = all(
            biaya.approval_stage == 'done' for biaya in self.biaya_peserta_ids
        )
        all_external_done = True  # Default True jika tidak ada pengikut eksternal
        if self.pengikut_eksternal and self.biaya_external_follower_ids:
            all_external_done = all(
                biaya.approval_stage == 'done' for biaya in self.biaya_external_follower_ids
            )

        # Jika SPPD Kantor Cabang dan belum di-review GM Cabang untuk biaya, jangan dulu ke review_biaya_done
        # State 'waiting_for_review_biaya' di SPPD utama itu untuk GM Cabang me-review biaya yg sdh diinput stafnya
        if self.is_cabang_sppd and self.state == 'sppd_approved_input_biaya':
            _logger.info("SPPD Cabang %s menunggu submit biaya dari staf, belum masuk _check_all_biaya_done",
                         self.name)
            return

        if self.is_cabang_sppd and self.state == 'waiting_for_review_biaya':
            # Untuk SPPD Cabang, setelah semua biaya (internal & eksternal) di-approve oleh GM Cabang
            # maka status SPPD bisa lanjut.
            # Kita asumsikan approval_gm_cabang di setiap item biaya menandakan approval GM.
            all_gm_approved_internal = all(b.approval_gm_cabang for b in self.biaya_peserta_ids)
            all_gm_approved_external = True
            if self.pengikut_eksternal and self.biaya_external_follower_ids:
                all_gm_approved_external = all(b.approval_gm_cabang for b in self.biaya_external_follower_ids)

            if all_gm_approved_internal and all_gm_approved_external:
                # Lanjut ke Kadiv Keuangan Pusat untuk transfer
                # Ini adalah contoh, alur sebenarnya mungkin beda di SPPD utama vs di item biaya
                # Untuk saat ini, jika semua biaya sudah diapprove GM, anggap review biaya selesai di level cabang.
                # State SPPD utama bisa jadi 'review_biaya_done' atau state lain yang menunggu transfer dari pusat.
                # Kita samakan dengan alur pusat, setelah semua biaya item 'done', sppd jadi 'review_biaya_done'
                if all_internal_done and all_external_done:
                    self.state = 'review_biaya_done'
                    self.message_post(body=_(
                        "Seluruh biaya peserta (internal & eksternal) untuk SPPD Cabang telah selesai di-review di levelnya masing-masing."))
            return

        # Untuk SPPD Pusat atau SPPD Cabang yang sudah melewati tahap review GM biaya
        if all_internal_done and all_external_done and self.state not in ['draft', 'sppd_approved_input_biaya']:
            # Hanya ubah state jika belum done atau running
            if self.state != 'review_biaya_done' and self.state != 'running' and self.state != 'done':
                self.state = 'review_biaya_done'
                self.message_post(
                    body=_("Seluruh biaya peserta (internal & eksternal) telah selesai di-review.")
                )


# --- Model untuk Rincian Biaya Pengikut Eksternal (Line) ---
class HrLeaveDinasExternalFollowerBiayaLine(models.Model):
    _name = 'hr.leave.dinas.external.follower.biaya.line'
    _description = 'Rincian Biaya Pengikut Eksternal Dinas'

    external_dinas_biaya_id = fields.Many2one(
        'hr.leave.dinas.external.follower.biaya',
        string='Referensi Biaya Pengikut Eksternal',
        ondelete='cascade',
        required=True,
        index=True
    )
    komponen_id = fields.Many2one('dinas.komponen', string='Komponen')
    jenis_lokasi = fields.Selection([
        ('ibu_kota', 'Ibu Kota Provinsi'),
        ('non_ibu_kota', 'Non Ibu Kota Provinsi'),
    ])
    golongan = fields.Selection([
        ('direksi', 'Dewan Komisaris / Direksi'),
        ('ks', 'KS/KDIV/VP/Setingkat/GM'),
        ('manager_bidang', 'Manager Bidang'),
        ('manager_sub', 'Manager Sub Bidang / Manager Unit'),
        ('staf', 'Staf'),
        ('eksternal_umum', 'Eksternal Umum'), # Tambah atau sesuaikan ini
    ], string='Golongan') # Dibiarkan sama dulu
    jumlah = fields.Monetary(string='Jumlah (Rp)')
    satuan = fields.Char(string='Satuan',
                         help='Format satuan biaya. Contoh: "Rp / Hari", "Rp / Perjalanan".')
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        default=lambda self: self.env.company.currency_id.id,
        required=True
    )

    @api.constrains('satuan')
    def _check_valid_satuan_external(self):
        allowed_keywords = ['hari', 'minggu', 'bulan', 'tahun', 'perjalanan']
        # Tambahkan satuan fixed yang diizinkan (dalam bentuk lowercase dan bersih)
        allowed_fixed_units = ['rp', 'rupiah', 'paket', 'unit', 'buah', 'set']

        for rec in self:
            if rec.satuan:
                # Bersihkan input: hilangkan simbol selain huruf, angka, spasi, lalu lowercase
                # Mungkin kita perlu lebih hati-hati agar tidak menghilangkan "/" jika itu bagian dari format
                # Tapi untuk matching keyword, pembersihan awal ini oke.
                satuan_input_lower = rec.satuan.lower()
                satuan_bersih_untuk_keyword = re.sub(r'[^a-z0-9\s]', '', satuan_input_lower).strip()

                # Cek apakah ada keyword waktu atau "perjalanan"
                contains_time_keyword = any(kw in satuan_bersih_untuk_keyword for kw in allowed_keywords)
                # Cek apakah satuan adalah salah satu dari unit fixed yang diizinkan
                is_allowed_fixed_unit = satuan_bersih_untuk_keyword in allowed_fixed_units

                if not (contains_time_keyword or is_allowed_fixed_unit):
                    # Jika tidak mengandung keyword waktu DAN bukan unit fixed yang diizinkan
                    raise UserError(_(
                        "Satuan '%s' pada komponen '%s' tidak dikenali.\n"
                        "Gunakan format seperti 'Rp / Hari', 'Rp / Perjalanan', atau satuan tunggal seperti 'Rp', 'Paket'."
                    ) % (rec.satuan, rec.komponen_id.name if rec.komponen_id else 'Tanpa Nama'))


class HrLeaveDinasExtendApproval(models.Model):
    _name = 'hr.leave.dinas.extend.approval'
    _description = 'Approval Perpanjangan Hari Dinas'
    _order = 'sequence asc'

    leave_dinas_id = fields.Many2one('hr.leave.dinas', string='SPPD', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Approver', required=True)
    state = fields.Selection([
        ('waiting', 'Menunggu Persetujuan'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ], string='Status', default='waiting')
    sequence = fields.Integer(string='Urutan', default=10)
    is_director = fields.Boolean(string='Direksi')
    approval_type = fields.Selection([
        ('mb', 'Manager Bidang'),
        ('kadiv', 'Kadiv'),
        ('gm_cabang_extend', 'GM Cabang (Perpanjangan)'),
        ('dirop', 'Direktur Operasional'),
        ('dirkeu', 'Direktur Keuangan'),
        ('dirut', 'Direktur Utama'),
    ], string='Jenis')
    is_my_turn = fields.Boolean(string='Saya Approver Aktif', compute='_compute_is_my_turn')

    @api.depends('state', 'leave_dinas_id.extend_approval_ids.state')
    def _compute_is_my_turn(self):
        current_uid = self.env.uid
        for rec in self:
            is_turn = False
            if rec.state == 'waiting' or rec.employee_id.user_id.id == current_uid:
                approvals = rec.leave_dinas_id.extend_approval_ids.sorted(key=lambda a: a.sequence)
                for approval in approvals:
                    if approval.state == 'waiting':
                        is_turn = approval.id == rec.id
                        break
            rec.is_my_turn = is_turn

    def _validate_current_user_as_approver(self):
        """Validasi umum apakah user saat ini adalah approver yang ditugaskan."""
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_('Data approver di baris persetujuan ini kosong. Harap hubungi Administrator.'))

        current_user_employee = self.env.user.employee_id
        if not current_user_employee:
            raise UserError(_('User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan aksi.'))

        if self.employee_id != current_user_employee:
            raise UserError(_('Anda (%s) bukan approver (%s) yang ditugaskan untuk tahap ini.')
                            % (current_user_employee.name, self.employee_id.name))

        if self.state != 'waiting':
            raise UserError(_('Permintaan persetujuan ini sudah diproses sebelumnya (%s).') % self.state)

    def action_approve(self):
        self.ensure_one()
        self._validate_current_user_as_approver()  # Panggil validasi umum

        # Validasi spesifik berdasarkan approval_type (jika ada)
        # Untuk 'gm_cabang_extend', employee_id sudah di-set oleh wizard sebagai GM Cabang yang benar.
        # Untuk 'dirut', employee_id sudah di-set oleh wizard sebagai Dirut yang benar.
        # Validasi struktur organisasi terkini untuk MB/Kadiv Pusat:
        if self.approval_type in ['mb', 'kadiv']:
            # _get_expected_approver_employee_ids ada di hr.leave.dinas (SPPD)
            # Ini untuk memastikan jika ada perubahan struktur, user yg approve masih sah
            valid_approver_ids = self.leave_dinas_id._get_expected_approver_employee_ids()
            if self.env.user.employee_id.id not in valid_approver_ids and self.employee_id.id not in valid_approver_ids:  # Double check
                # Bisa jadi self.employee_id adalah yg lama, dan user yg login adalah penggantinya
                # Atau self.employee_id adalah yg baru, tapi user yg login bukan dia
                # Untuk simpelnya, kita cek user yg login saja
                if self.env.user.employee_id.id not in valid_approver_ids:
                    raise UserError(
                        _('Struktur organisasi telah berubah. Anda tidak lagi tercatat sebagai approver (%s) yang sah untuk SPPD ini.') % self.get_approval_type_display())

        # Validasi giliran (jika ada multiple approvers dalam satu SPPD extend request)
        # Untuk skenario Cabang, hanya ada 1 approver (GM atau Dirut) jadi ini tidak terlalu kritikal,
        # tapi untuk Pusat yang berjenjang, ini penting.
        approvals_sorted = self.leave_dinas_id.extend_approval_ids.sorted(key=lambda a: a.sequence)
        for approval_item in approvals_sorted:
            if approval_item.state == 'waiting':
                if approval_item.id != self.id:  # Jika ada yang lain sebelum dia masih waiting
                    raise UserError(
                        _('Bukan giliran Anda untuk menyetujui. Persetujuan saat ini menunggu dari %s (%s).')
                        % (approval_item.employee_id.name, approval_item.get_approval_type_display()))
                break  # Jika ini yang pertama waiting, maka giliran dia

        # --- Lolos semua validasi ---
        self.state = 'approved'

        # Update SPPD utama (hr.leave.dinas)
        sppd = self.leave_dinas_id
        sppd.message_post(body=_(
            "<b>%s</b> telah MENYETUJUI perpanjangan hari dinas. (Tahap: <i>%s</i>)"
        ) % (self.employee_id.name, self.get_approval_type_display()))  # Gunakan display name

        # Cek apakah ada approver selanjutnya atau semua sudah approve
        next_approver_record = next((a for a in approvals_sorted if a.id != self.id and a.state == 'waiting'),
                                    None)  # Cari yang lain yg masih waiting

        if next_approver_record:
            sppd.extend_state = f'waiting_{next_approver_record.approval_type}'
            # Pesan di chatter SPPD sudah ter-post di atas
        else:
            # Tidak ada approver lain yang waiting, berarti semua sudah approve
            sppd.action_check_extend_done()  # Panggil method di SPPD untuk finalisasi

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_reject(self):
        self.ensure_one()
        self._validate_current_user_as_approver()  # Panggil validasi umum

        # Validasi spesifik (sama seperti di action_approve jika perlu)
        if self.approval_type in ['mb', 'kadiv']:
            valid_approver_ids = self.leave_dinas_id._get_expected_approver_employee_ids()
            if self.env.user.employee_id.id not in valid_approver_ids:
                raise UserError(
                    _('Struktur organisasi telah berubah. Anda tidak lagi tercatat sebagai approver (%s) yang sah untuk SPPD ini.') % self.get_approval_type_display())

        # Validasi giliran
        approvals_sorted = self.leave_dinas_id.extend_approval_ids.sorted(key=lambda a: a.sequence)
        for approval_item in approvals_sorted:
            if approval_item.state == 'waiting':
                if approval_item.id != self.id:
                    raise UserError(
                        _('Bukan giliran Anda untuk menolak. Persetujuan saat ini menunggu dari %s (%s).')
                        % (approval_item.employee_id.name, approval_item.get_approval_type_display()))
                break

        # --- Lolos semua validasi ---
        self.state = 'rejected'

        sppd = self.leave_dinas_id
        sppd.extend_state = 'rejected'  # Set status perpanjangan di SPPD utama jadi ditolak
        sppd.state = 'running'  # Kembalikan status SPPD utama ke 'running' (atau state sebelum 'pause')

        sppd.message_post(body=_(
            "<b>%s</b> telah MENOLAK permintaan perpanjangan hari dinas. (Tahap: <i>%s</i>)"
        ) % (self.employee_id.name, self.get_approval_type_display()))

        # Reset data perpanjangan di SPPD utama (opsional, bisa juga tidak direset agar ada histori)
        # Jika mau direset:
        # sppd.extend_date_to = False
        # sppd.extend_reason = False
        # sppd.extend_approval_ids.unlink() # Hapus semua baris approval jika ditolak (hati-hati) #
        # Atau biarkan saja, extend_state = 'rejected' sudah cukup menandakan.

        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def get_approval_type_display(self):
        """Helper untuk mendapatkan display name dari approval_type."""
        self.ensure_one()
        return dict(self._fields['approval_type'].selection).get(self.approval_type, self.approval_type)


class HrLeaveDinasParticipantExtendApproval(models.Model):
    _name = 'hr.leave.dinas.participant.extend.approval'
    _description = 'Approval Perpanjangan Hari Dinas per Peserta'
    _order = 'sequence asc'

    # Relasi ke parent (bisa ke biaya internal atau eksternal)
    # Karena Odoo tidak mendukung Many2one polimorfik secara langsung,
    # cara termudah adalah punya DUA field Many2one dan constraint salah satu harus diisi.
    # Atau, jika nama field di biaya internal dan eksternal SAMA (misal 'extend_approval_line_ids')
    # maka field Many2one di sini bisa lebih generik namanya.
    # Kita coba dengan satu field Many2one ke SPPD utama dulu, dan nanti di-filter dari SPPD utama.
    # Namun, lebih baik jika langsung ke record biayanya.
    # Mari kita buat dua field Many2one untuk sementara, lalu kita pilih yang paling praktis.

    # Opsi 1: Dua field Many2one
    biaya_peserta_id = fields.Many2one('hr.leave.dinas.biaya', string='Biaya Peserta Internal', ondelete='cascade')
    biaya_external_id = fields.Many2one('hr.leave.dinas.external.follower.biaya', string='Biaya Pengikut Eksternal', ondelete='cascade')
    # Field dummy untuk 'parent' agar bisa dipakai di view (jika perlu)
    # biaya_participant_ref_id akan diisi oleh salah satu dari atas.
    # Untuk kemudahan, kita buat satu field Many2one ke SPPD utama saja, lalu di wizard kita set target peserta
    # Ini akan menyederhanakan relasi, tapi butuh filter tambahan.
    # **REVISI**: Lebih baik langsung ke record biaya pesertanya.
    # Kita buat satu field Char untuk model parent, dan Integer untuk ID parent.
    # Atau, karena kita ingin alur approvalnya sama, kita bisa "repurpose" field di HrLeaveDinasExtendApproval yang sudah ada.
    # Mari kita buat model baru agar bersih.

    # Field Many2one ini akan merujuk ke record biaya peserta (internal atau eksternal)
    # Ini agak tricky karena targetnya bisa dua model berbeda.
    # Alternatif paling mudah adalah punya DUA field One2many di model biaya:
    # - Di HrLeaveDinasBiaya: participant_extend_approval_ids = fields.One2many('hr.leave.dinas.participant.extend.approval', 'biaya_peserta_id')
    # - Di HrLeaveDinasExternalFollowerBiaya: participant_extend_approval_ids = fields.One2many('hr.leave.dinas.participant.extend.approval', 'biaya_external_id')

    # Di model approval:
    biaya_peserta_id = fields.Many2one('hr.leave.dinas.biaya', string='Ref Biaya Internal', ondelete='cascade', index=True)
    biaya_external_id = fields.Many2one('hr.leave.dinas.external.follower.biaya', string='Ref Biaya Eksternal', ondelete='cascade', index=True)
    # Untuk mempermudah, kita ambil SPPD utamanya juga
    leave_dinas_id = fields.Many2one('hr.leave.dinas', string='SPPD Induk', store=True, readonly=True,
                                     compute='_compute_leave_dinas_id', index=True)

    employee_id = fields.Many2one('hr.employee', string='Approver', required=True)
    state = fields.Selection([
        ('waiting', 'Menunggu Persetujuan'),
        ('approved', 'Disetujui'),
        ('rejected', 'Ditolak'),
    ], string='Status', default='waiting', required=True, copy=False)
    sequence = fields.Integer(string='Urutan', default=10)
    approval_type = fields.Selection([ # Bisa disamakan dengan yang lama atau disesuaikan
        ('mb', 'Manager Bidang'),
        ('kadiv', 'Kadiv'),
        ('gm_cabang_extend', 'GM Cabang (Perpanjangan)'),
        ('dirop', 'Direktur Operasional'),
        ('dirkeu', 'Direktur Keuangan'),
        ('dirut', 'Direktur Utama'),
    ], string='Jenis Approver', required=True)
    is_my_turn = fields.Boolean(string='Giliran Saya', compute='_compute_is_my_turn')
    # Tambahkan field untuk catatan/alasan approval/rejection jika perlu
    approval_notes = fields.Text("Catatan Persetujuan/Penolakan")

    @api.depends('biaya_peserta_id', 'biaya_external_id')
    def _compute_leave_dinas_id(self):
        for rec in self:
            if rec.biaya_peserta_id:
                rec.leave_dinas_id = rec.biaya_peserta_id.leave_dinas_id
            elif rec.biaya_external_id:
                rec.leave_dinas_id = rec.biaya_external_id.leave_dinas_id
            else:
                rec.leave_dinas_id = False

    # Method _compute_is_my_turn, _validate_current_user_as_approver, action_approve, action_reject
    # akan sangat mirip dengan yang ada di HrLeaveDinasExtendApproval sebelumnya.
    # Perbedaannya adalah saat semua approver sudah approve, kita update field
    # `extend_deviation_state` dan `deviated_actual_date_to` di `biaya_peserta_id` atau `biaya_external_id`.

    def _get_parent_biaya_record(self):
        """Helper untuk mendapatkan record biaya parent (internal atau eksternal)."""
        self.ensure_one()
        return self.biaya_peserta_id or self.biaya_external_id

    @api.depends('state', 'biaya_peserta_id.participant_extend_approval_ids.state',
                 'biaya_external_id.participant_extend_approval_ids.state')
    def _compute_is_my_turn(self):
        # Logic _compute_is_my_turn (mirip yang lama, tapi source list approval dari parent biaya)
        # ... (implementasi seperti di HrLeaveDinasExtendApproval, tapi ambil list approval dari parent_biaya_record.participant_extend_approval_ids)
        for rec in self:
            is_turn = False
            parent_biaya_record = rec._get_parent_biaya_record()
            if parent_biaya_record and rec.state == 'waiting':
                current_user_employee = rec.env.user.employee_id
                if rec.employee_id == current_user_employee:
                    # Cek apakah ini approver pertama yang waiting dalam sequence
                    approvals_sorted = parent_biaya_record.participant_extend_approval_ids.sorted(key=lambda a: a.sequence)
                    for approval_item in approvals_sorted:
                        if approval_item.state == 'waiting':
                            if approval_item.id == rec.id:
                                is_turn = True
                            break
            rec.is_my_turn = is_turn

    def action_approve(self):
        # Validasi (mirip yang lama: _validate_current_user_as_approver, validasi giliran)
        # ...
        self.ensure_one()
        # Panggil validasi umum (seperti di model lama)
        # self._validate_current_user_as_approver()
        # Pastikan user yang login adalah employee_id di baris approval ini dan state masih 'waiting'
        if self.env.user.employee_id != self.employee_id or self.state != 'waiting':
            raise UserError(_("Anda tidak berhak melakukan aksi ini atau sudah diproses."))


        self.write({'state': 'approved', 'approval_notes': 'Disetujui otomatis via sistem (contoh)'}) # Tambah inputan notes jika ada fieldnya

        parent_biaya_record = self._get_parent_biaya_record()
        if parent_biaya_record:

            # Cek apakah semua approval untuk peserta ini sudah selesai
            all_approved_for_participant = all(
                appr.state == 'approved' for appr in parent_biaya_record.participant_extend_approval_ids
            )
            if all_approved_for_participant:
                parent_biaya_record.write({
                    'extend_deviation_state': 'approved',
                    'is_deviated': True, # Pastikan ini juga di-set
                    'deviation_type': 'extend_days', # Pastikan ini juga di-set
                })
        return True


    def action_reject(self):
        # Validasi (mirip yang lama)
        # ...
        self.ensure_one()
        if self.env.user.employee_id != self.employee_id or self.state != 'waiting':
            raise UserError(_("Anda tidak berhak melakukan aksi ini atau sudah diproses."))

        self.write({'state': 'rejected', 'approval_notes': 'Ditolak otomatis via sistem (contoh)'}) # Tambah inputan notes jika ada fieldnya

        parent_biaya_record = self._get_parent_biaya_record()
        if parent_biaya_record:
            parent_biaya_record.write({'extend_deviation_state': 'rejected'})
            parent_biaya_record.leave_dinas_id.message_post(body=_(
                "Perpanjangan untuk peserta <b>%s</b> tahap <i>%s</i> oleh <b>%s</b>: Ditolak."
            ) % (parent_biaya_record.name,
                 dict(self._fields['approval_type'].selection).get(self.approval_type),
                 self.employee_id.name))
        return True


class HrLeaveDinasUnexpectedCost(models.Model):
    _name = 'hr.leave.dinas.unexpected.cost'
    _description = 'Biaya Tak Terduga Dinas'
    _order = 'id desc'

    leave_dinas_id = fields.Many2one(
        'hr.leave.dinas',
        string='Referensi SPPD',
        ondelete='cascade',
        required=True
    )
    name = fields.Char(string='Keterangan Biaya', required=True)
    amount = fields.Monetary(string='Jumlah Biaya', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        default=lambda self: self.env.company.currency_id.id
    )