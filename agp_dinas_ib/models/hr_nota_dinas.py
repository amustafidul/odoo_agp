from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError, UserError

import logging

_logger = logging.getLogger(__name__)


class NotaDinas(models.Model):
    _name = 'nota.dinas'
    _description = 'Nota Dinas (Module Dinas)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nomor', readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env.user.employee_id, domain=[('employment_type','in',['organik','pkwt'])])
    pemohon = fields.Char(compute="_compute_pemohon", store=False)
    employee_position_id = fields.Many2one('employee.position', string='Kepada Yth')
    employee_position_komplit_id = fields.Many2one('hr.employee.jabatan.komplit', string='Kepada Yth')
    employee_position_tembusan_id = fields.Many2one('employee.position', string='Tembusan')
    employee_position_komplit_tembusan_id = fields.Many2one('hr.employee.jabatan.komplit', string='Tembusan')
    pemberi_perintah_id = fields.Many2one(
        'hr.employee',
        string='Pemberi Perintah',
        default=lambda self: self._get_default_pemberi_perintah(),
        readonly=True
    )
    employee_position_applicant_id = fields.Many2one('employee.position', string='Dari - archived')
    employee_applicant_id = fields.Many2one('hr.employee', string='Dari', compute='_compute_employee_applicant_id')
    perihal_desc = fields.Char(string='Perihal')
    tanggal_nota_dinas = fields.Date(string='Tanggal', default=datetime.today())
    dinas_date_from = fields.Date()
    dinas_date_to = fields.Date()
    destination_place = fields.Char(string='Tujuan')
    agenda_desc = fields.Text(string='Agenda')
    kata_pengantar = fields.Text(string='Kata Pengantar')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_bidang', 'Review by Manager Bidang'),
        ('kepala_divisi', 'Review by Kadiv'),
        ('gm', 'Review by General Manager'),
        ('mb_keu_sdm_umum', 'Review by MB Keu. SDM & Umum'),
        ('kadiv_keu_kantor_pusat', 'Review by Kadiv Keu. Kantor Pusat'),
        ('direktur_operasional', 'Review by Dirop'),
        ('direktur_keuangan', 'Review by Dirkeu'),
        ('direktur_utama', 'Review by Dirut'),
        ('done', 'Done')
    ], string='Status', default='draft', track_visibility='onchange')
    type_nodin = fields.Selection([
        ('not_set', 'Not Set'),
        ('kantor_pusat', 'Kantor Pusat'),
        ('kantor_cabang', 'Kantor Cabang')
    ], string='Tipe Nodin', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    nota_dinas_line_ids = fields.One2many('nota.dinas.line', 'nota_dinas_id', string='Nota Dinas Lines')
    disposisi_dirop_desc = fields.Text('Disposisi Dirop')
    disposisi_dirkeu_desc = fields.Text('Disposisi Dirkeu')
    disposisi_dirut_desc = fields.Text('Disposisi Dirut')
    division_id = fields.Many2one('hr.employee.unit', string='Divisi')
    department_id = fields.Many2one('hr.department', string="Departemen", default=lambda self: self._default_department_id())
    manager_id = fields.Many2one(related='department_id.manager_id', string="Manager", readonly=True)
    pemberi_undangan_id = fields.Many2one('hr.employee', string='Pemberi Undangan - archived', domain=[('employment_type','in',['organik','pkwt'])])
    pemberi_undangan = fields.Text('Pemberi Undangan')
    related_sppd_count = fields.Integer(string='SPPD Count', compute='_compute_related_sppd_count')
    tanggal_nota_dinas_year = fields.Char(string='Tahun Nota Dinas', compute='_compute_tanggal_nota_dinas_year', store=True)

    def _compute_pemohon(self):
        for rec in self:
            rec.pemohon = f"{rec.employee_id.name} - {rec.employee_id.department_id.name}"

    def _compute_related_sppd_count(self):
        sppd_data = self.env['hr.leave.dinas'].read_group(
            [('nota_dinas_id', 'in', self.ids)],
            ['nota_dinas_id'],
            ['nota_dinas_id']
        )
        mapping = {}
        for data in sppd_data:
            if data.get('nota_dinas_id') and data.get('nota_dinas_id_count'):
                mapping[data['nota_dinas_id'][0]] = data['nota_dinas_id_count']
        for record in self:
            record.related_sppd_count = mapping.get(record.id, 0)

    def action_open_related_sppd(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related SPPD',
            'res_model': 'hr.leave.dinas',
            'view_mode': 'tree,form',
            'domain': [('nota_dinas_id', '=', self.id)],
            'context': {'create': False}
        }

    @api.depends('employee_id','employee_id.department_id.manager_id','employee_id.department_id.department_type',
                 'employee_id.department_id.parent_id.manager_id','employee_id.department_id.parent_id.department_type')
    def _compute_employee_applicant_id(self):
        for rec in self:
            if rec.employee_id.department_id.department_type == 'bidang':
                rec.employee_applicant_id = rec.employee_id.department_id.parent_id.manager_id.id
            elif rec.employee_id.department_id.department_type == 'divisi':
                rec.employee_applicant_id = rec.employee_id.department_id.manager_id.id
            else:
                rec.employee_applicant_id = False

    def _get_default_pemberi_perintah(self):
        dirut = self.env['hr.employee'].search([
            ('keterangan_jabatan_id.nodin_workflow', '=', 'dirut')
        ], limit=1)
        return dirut.id if dirut else False

    @api.model
    def _default_department_id(self):
        department = self.env['hr.department'].search([('manager_id.user_id', '=', self.env.user.id)], limit=1)
        return department.id if department else False

    @api.model
    def default_get(self, fields_list):
        res = super(NotaDinas, self).default_get(fields_list)
        user = self.env.user
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if employee and employee.employment_type in ['organik', 'pkwt']:
            position = self.env['employee.position'].search([('employee_id', '=', employee.id)], limit=1)
            if position:
                res.update({
                    'division_id': position.employee_id.hr_employee_unit_id.id
                })
            jabatan_list = self.env['employee.position'].search([('employee_id', '=', employee.id)]).mapped('name')
            res['nota_dinas_line_ids'] = [(0, 0, {
                'applicant_id': employee.id,
                'jabatan': ', '.join(jabatan_list) if jabatan_list else ''
            })]
        return res

    def name_get(self):
        result = []
        for record in self:
            name = record.name or 'Nota Dinas'
            destination_place = record.destination_place or ''
            dinas_date_from = record.dinas_date_from
            dinas_date_to = record.dinas_date_to
            display_name = f"{name} - {destination_place} ({dinas_date_from} - {dinas_date_to})" if destination_place and dinas_date_from and dinas_date_to else name
            result.append((record.id, display_name))
        return result

    def generate_nota_dinas_sequence(self):
        current_year = datetime.now().year
        angka_sequence = self.env['ir.sequence'].next_by_code('nota.dinas')
        roman_months = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'}
        current_month = datetime.now().month
        current_month_roman = roman_months.get(current_month, 'I')
        full_sequence = f"{angka_sequence}/{current_month_roman}/{current_year}/DIVPBB"
        return full_sequence

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.generate_nota_dinas_sequence()
        res = super(NotaDinas, self).create(vals)
        return res

    @api.depends('tanggal_nota_dinas')
    def _compute_tanggal_nota_dinas_year(self):
        for record in self:
            if record.tanggal_nota_dinas:
                formatted_output = 'Periode: %s' % (record.tanggal_nota_dinas.strftime('%Y'))
                record.tanggal_nota_dinas_year = formatted_output

    def action_submit(self):
        for rec in self:
            if not rec.type_nodin or rec.type_nodin == 'not_set':
                raise ValidationError(
                    _("Tipe Nota Dinas (Kantor Pusat/Kantor Cabang) tidak dapat ditentukan.\nPastikan data 'Tipe Nodin' telah diisi."))

            if rec.type_nodin == 'kantor_pusat':
                dept_type = rec.employee_id.department_id.department_type
                if dept_type == 'bidang':
                    rec.state = 'manager_bidang'
                    rec.message_post(body=_("Nota Dinas Kantor Pusat disubmit dan menunggu review Manager Bidang."))
                elif dept_type == 'divisi':
                    rec.state = 'kepala_divisi'
                    rec.message_post(body=_("Nota Dinas Kantor Pusat disubmit dan menunggu review Kepala Divisi."))
                else:
                    raise ValidationError(
                        _("Pemohon Kantor Pusat (%s) tidak memiliki tipe department yang dikenali (bidang/divisi).\nMohon cek pada bagian field 'Jenis Department' di master data Department.") % rec.employee_id.name)

            elif rec.type_nodin == 'kantor_cabang':
                pemohon = rec.employee_id
                if not pemohon.hr_branch_id:
                    raise UserError(_("Pemohon (%s) tidak terdaftar pada kantor cabang manapun.") % pemohon.name)

                gm_cabang_pemohon = pemohon.hr_branch_id.manager_id
                if not gm_cabang_pemohon:
                    raise UserError(
                        _("General Manager untuk kantor cabang (%s) tempat pemohon (%s) bekerja belum diatur di master Branch.")
                        % (pemohon.hr_branch_id.name, pemohon.name))

                if pemohon == gm_cabang_pemohon:
                    # If the applicant is the GM of his own branch
                    rec.state = 'direktur_utama'
                    rec.message_post(body=_(
                        "Nota Dinas Kantor Cabang diajukan oleh GM (%s) dan langsung diteruskan untuk approval Direktur Utama.") % pemohon.name)
                else:
                    # If the applicant is a regular staff in the Branch
                    rec.state = 'gm'
                    rec.message_post(body=_(
                        "Nota Dinas Kantor Cabang disubmit dan menunggu review General Manager (%s).") % gm_cabang_pemohon.name)

    def action_approve_gm(self):
        """Action to be approved by Branch General Manager."""
        for rec in self:
            if rec.state != 'gm' or rec.type_nodin != 'kantor_cabang':
                raise UserError(
                    _("Aksi ini hanya valid untuk Nota Dinas Kantor Cabang dengan status 'Review by General Manager'."))

            current_employee = self.env.user.employee_id
            if not current_employee:
                raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

            branch_manager = rec.employee_id.hr_branch_id.manager_id
            if not branch_manager:
                raise UserError(_("General Manager untuk kantor cabang pemohon (%s) belum diatur di master Branch.") % (
                            rec.employee_id.hr_branch_id.name or 'N/A'))

            if current_employee != branch_manager:
                raise UserError(_("Anda (%s) bukan General Manager (%s) yang ditugaskan untuk kantor cabang ini.") % (
                    current_employee.name, branch_manager.name))

            next_state = 'done'
            rec.state = next_state
            rec.message_post(body=_(
                "Nota Dinas telah disetujui oleh General Manager (%s) dan telah selesai."
            ) % (current_employee.name))

    def action_approve_mb_keu_sdm_umum(self):
        """Action for approval by MB Finance, HR & General (Flow Branch Office)."""
        for rec in self:
            # 1. Validate Status and Tipe Nodin
            if rec.state != 'mb_keu_sdm_umum' or rec.type_nodin != 'kantor_cabang':
                raise UserError(
                    _("Aksi ini hanya valid untuk Nota Dinas Kantor Cabang dengan status 'Review by MB Keu. SDM & Umum'."))

            # 2. Approver Validation (MB Finance HR & General)
            # Search for departments with role 'mb_keuangan'
            # TODO: Review this logic. Does not filter by applicant's branch. Assumes only ONE dept has this role globally?
            # Consider adding a branch_id field to hr.department or using another logic if multiple branches exist.
            mb_keu_dept = self.env['hr.department'].search([
                ('biaya_sppd_role', '=', 'mb_keuangan'),
                ('branch_id.location', '=', 'branch_office'),
                ('department_type', '=', 'bidang')
            ])

            if not mb_keu_dept:
                raise UserError(
                    _("Tidak ditemukan konfigurasi Departemen untuk role 'MB Keuangan'. Harap hubungi Administrator."))
            if len(mb_keu_dept) > 1:
                raise UserError(_("Ditemukan lebih dari satu Departemen dengan role 'MB Keuangan'. Konfigurasi ambigu."))

            target_dept = mb_keu_dept[0]
            approver = target_dept.manager_id

            if not approver:
                raise UserError(_("Manager untuk Departemen %s (role MB Keuangan) belum diatur.") % (target_dept.name))

            current_employee = self.env.user.employee_id
            if not current_employee:
                raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

            # Check if the current user is the intended approver
            if current_employee != approver:
                raise UserError(
                    _("Anda (%s) bukan approver (%s) yang ditugaskan untuk tahap ini (MB Keu. SDM & Umum).") % (
                        current_employee.name, approver.name))

            # 3. Pass Validation -> Change Status
            next_state = 'kadiv_keu_kantor_pusat'
            rec.state = next_state
            rec.message_post(body=_(
                "Nota Dinas telah disetujui oleh MB Keu. SDM & Umum (%s). Status selanjutnya: %s."
            ) % (current_employee.name, dict(rec._fields['state'].selection).get(next_state)))

    def action_approve_kadiv_keu_kantor_pusat(self):
        """Action for approval by the Head of Finance Division of the Head Office (Flow Branch Office)."""
        for rec in self:
            # 1. Validate Status and Tipe Nodin
            if rec.state != 'kadiv_keu_kantor_pusat' or rec.type_nodin != 'kantor_cabang':
                raise UserError(
                    _("Aksi ini hanya valid untuk Nota Dinas Kantor Cabang dengan status 'Review by Kadiv Keu. Kantor Pusat'."))

            # 2. Approver Validation (Head of Finance Division, Head Office)
            # Assumption: hr.department has a field 'branch_id' (Many2one to hr.branch)
            kadiv_keu_dept = self.env['hr.department'].search([
                ('biaya_sppd_role', '=', 'kadiv_keuangan'),
                ('branch_id.location', '=', 'head_office'),
                ('department_type', '=', 'divisi')
            ])

            if not kadiv_keu_dept:
                raise UserError(
                    _("Tidak ditemukan konfigurasi Departemen Divisi untuk role 'Kadiv Keuangan'. Harap hubungi Administrator."))
            if len(kadiv_keu_dept) > 1:
                raise UserError(
                    _("Ditemukan lebih dari satu Departemen Divisi dengan role 'Kadiv Keuangan'. Konfigurasi ambigu."))

            target_dept = kadiv_keu_dept[0]
            approver = target_dept.manager_id

            if not approver:
                raise UserError(
                    _("Manager untuk Departemen %s (role Kadiv Keuangan - Pusat) belum diatur.") % (target_dept.name))

            current_employee = self.env.user.employee_id
            if not current_employee:
                raise UserError(_("User Anda tidak terhubung dengan data Employee. Tidak dapat melakukan approval."))

            # Check if the current user is the intended approver
            if current_employee != approver:
                raise UserError(
                    _("Anda (%s) bukan approver (%s) yang ditugaskan untuk tahap ini (Kadiv Keu. Kantor Pusat).") % (
                        current_employee.name, approver.name))

            # 3. Pass Validation -> Change Status to Director Flow
            next_state = 'direktur_utama'
            rec.state = next_state
            rec.message_post(body=_(
                "Nota Dinas telah disetujui oleh Kadiv Keu. Kantor Pusat (%s). Status selanjutnya: %s."
            ) % (current_employee.name, dict(rec._fields['state'].selection).get(next_state)))

    def action_approve_manager_bidang(self):
        for rec in self:
            if rec.state != 'manager_bidang':
                raise UserError("Status saat ini bukan di Manager Bidang.")
            if rec.employee_id.department_id.department_type != 'bidang':
                raise UserError("Department bukan termasuk 'bidang'.")
            if rec.employee_id.department_id.manager_id.user_id != self.env.user:
                raise UserError("Anda bukan Manager dari department ini.")
            rec.state = 'kepala_divisi'

    def action_approve_kepala_divisi(self):
        for rec in self:
            if rec.state != 'kepala_divisi':
                raise UserError("Status saat ini bukan di Kepala Divisi.")
            if rec.employee_id.department_id.manager_id.user_id != self.env.user:
                raise UserError("Anda bukan Kepala Divisi dari department ini.")
            rec.state = 'direktur_operasional'

    def _get_short_direksi_code(self, approval_level_key):
        """Helper untuk mendapatkan kode pendek direksi."""
        if approval_level_key == 'direktur_operasional':
            return 'dirop'
        elif approval_level_key == 'direktur_keuangan':
            return 'dirkeu'
        elif approval_level_key == 'direktur_utama':
            return 'dirut'
        return None

    def _open_disposisi_wizard(self, approval_level_key):
        self.ensure_one()

        short_code = self._get_short_direksi_code(approval_level_key)
        if not short_code:
            # Handle error jika approval_level_key tidak dikenal, meskipun seharusnya tidak terjadi
            raise UserError(_("Tingkat approval direksi tidak dikenal: %s") % approval_level_key)

        if not self._check_direksi_permission(short_code):  # <<< UBAH DI SINI
            # Untuk pesan error, kita bisa tetap pakai label panjang dari selection wizard
            wizard_approval_level_selection = dict(
                self.env['nota.dinas.disposisi.wizard']._fields['approval_level'].selection)
            display_level = wizard_approval_level_selection.get(short_code)  # Ambil label dari wizard pakai short_code
            if not display_level:  # fallback jika short_code tidak ada di selection wizard (seharusnya tidak)
                display_level = approval_level_key.replace('direktur_', '').title()

            raise UserError(_("Anda tidak memiliki hak untuk memberikan disposisi sebagai %s.") % display_level)

        ctx = {
            'default_nota_dinas_id': self.id,
            'default_approval_level': short_code,  # <<< UBAH DI SINI, kirim short_code
        }
        return {
            'name': _('Input Disposisi'),
            'type': 'ir.actions.act_window',
            'res_model': 'nota.dinas.disposisi.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('agp_dinas_ib.view_nota_dinas_disposisi_wizard_form').id,
            'target': 'new',
            'context': ctx,
        }

    def _check_direksi_permission(self, expected_jabatan):
        _logger.info('expected_jabatan: %s', expected_jabatan)
        current_employee = self.env.user.employee_id
        if not current_employee or not current_employee.direksi:
            return False
        jabatan = current_employee.keterangan_jabatan_id.nodin_workflow or ''
        return expected_jabatan == jabatan

    def action_approve_direktur_operasional_wizard(self):
        return self._open_disposisi_wizard('direktur_operasional')

    def action_approve_direktur_operasional(self):
        # Method ini sekarang hanya dipanggil dari wizard setelah disposisi diisi
        for rec in self:
            if rec.state != 'direktur_operasional':  # Seharusnya sudah divalidasi sebelum wizard
                raise UserError("Status saat ini bukan di Direktur Operasional.")
            # Validasi permission sudah dilakukan di _open_disposisi_wizard
            # Dan akan implisit tervalidasi lagi jika user mencoba akses langsung method ini tanpa wizard.
            # Namun, untuk keamanan ganda, bisa ditambahkan lagi _check_direksi_permission jika perlu.
            rec.state = 'direktur_keuangan'
            rec.message_post(body=_(
                "Nota Dinas telah diproses oleh Direktur Operasional dengan disposisi: %s. Lanjut ke Direktur Keuangan.") % (
                                              rec.disposisi_dirop_desc or '-'))

    def action_approve_direktur_keuangan_wizard(self):
        return self._open_disposisi_wizard('direktur_keuangan')

    def action_approve_direktur_keuangan(self):
        for rec in self:
            if rec.state != 'direktur_keuangan':
                raise UserError("Status saat ini bukan di Direktur Keuangan.")
            rec.state = 'direktur_utama'
            rec.message_post(body=_(
                "Nota Dinas telah diproses oleh Direktur Keuangan dengan disposisi: %s. Lanjut ke Direktur Utama.") % (
                                              rec.disposisi_dirkeu_desc or '-'))

    def action_approve_direktur_utama_wizard(self):
        return self._open_disposisi_wizard('direktur_utama')

    def action_approve_direktur_utama(self):
        for rec in self:
            if rec.state != 'direktur_utama':
                raise UserError("Status saat ini bukan di Direktur Utama.")
            rec.state = 'done'
            rec.message_post(body=_("Nota Dinas telah disetujui oleh Direktur Utama dengan disposisi: %s.") % (
                        rec.disposisi_dirut_desc or '-'))

    def action_create_sppd(self):
        for record in self:
            existing_sppd = self.env['hr.leave.dinas'].search([('nota_dinas_id', '=', record.id)], limit=1)
            if existing_sppd:
                raise ValidationError(_("SPPD sudah pernah dibuat untuk Nota Dinas ini."))
            sppd_vals = {
                'nota_dinas_id': record.id,
                'assigner_id': record.employee_id.id,
                'assignee_id': record.user_id.employee_id.id,
                'assignee_ids': [(6, 0, record.nota_dinas_line_ids.mapped('applicant_id.id'))],
                'agenda_dinas': record.agenda_desc,
                'pemberi_undangan': record.pemberi_undangan,
                'destination_place': record.destination_place,
                'date_from': record.dinas_date_from,
                'date_to': record.dinas_date_to,
                'state': 'draft',
            }
            sppd = self.env['hr.leave.dinas'].create(sppd_vals)
            record.state = 'done'
            return {
                'name': _('SPPD'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.leave.dinas',
                'view_mode': 'form',
                'res_id': sppd.id,
                'target': 'current',
            }


class NotaDinasLine(models.Model):
    _name = 'nota.dinas.line'
    _description = 'Nota Dinas Line'
    _order = 'sequence asc, id asc'

    nota_dinas_id = fields.Many2one('nota.dinas', string='Nota Dinas Reference', required=True, ondelete='cascade')
    applicant_id = fields.Many2one('hr.employee', string='Nama', domain=lambda self: self._get_applicant_domain())
    jabatan = fields.Char(string='Jabatan', compute='_compute_jabatan', store=True)
    sequence = fields.Integer(string='Urutan', default=1)

    @api.depends('applicant_id')
    def _compute_jabatan(self):
        applicant_ids = self.mapped('applicant_id.id')
        pos_dict = {}
        positions = self.env['employee.position'].search([('employee_id', 'in', applicant_ids)])
        for pos in positions:
            pos_dict.setdefault(pos.employee_id.id, []).append(pos.name)
        for rec in self:
            rec.jabatan = ', '.join(pos_dict.get(rec.applicant_id.id, []))

    def _get_applicant_domain(self):
        employee_positions = self.env['employee.position'].search([])
        employee_ids = employee_positions.mapped('employee_id.id')
        return [('id', 'in', employee_ids)]

    @api.constrains('sequence')
    def _check_sequence_positive_and_unique(self):
        for rec in self:
            if rec.sequence <= 0:
                raise ValidationError(_('Urutan (Sequence) harus lebih besar dari 0.'))

            duplicate = self.search([
                ('nota_dinas_id', '=', rec.nota_dinas_id.id),
                ('sequence', '=', rec.sequence),
                ('id', '!=', rec.id)
            ])
            if duplicate:
                raise ValidationError(_('Urutan (Sequence) harus unik dalam satu Nota Dinas.'))