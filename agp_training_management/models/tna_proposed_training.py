from odoo import models, fields, api
from odoo.exceptions import UserError


class TnaProposedTraining(models.Model):
    _name = 'tna.proposed.training'
    _description = 'Detail Usulan Kebutuhan Training (Line Item)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_id, sequence, id'

    submission_id = fields.Many2one(
        'tna.submission',
        string='Form Usulan TNA Induk',
        required=True,
        ondelete='cascade',
        index=True,
        help="Form usulan TNA tempat detail training ini berada."
    )
    sequence = fields.Integer(
        string='No. Urut',
        default=10,
        help="Nomor urut untuk tampilan di form usulan."
    )
    name = fields.Char(
        string='Nama Diklat/Workshop/Sertifikasi',
        required=True,
        tracking=True,
        help="Judul training yang diusulkan."
    )
    training_scope_id = fields.Many2one(
        'tna.training.scope',
        string='Lingkup Diklat/Training',
        tracking=True,
        help="Pilih lingkup atau kategori training yang sesuai."
    )
    description = fields.Text(
        string='Justifikasi & Deskripsi Kebutuhan',
        help="Jelaskan mengapa pelatihan ini dibutuhkan, apa tujuannya, dan manfaat yang diharapkan."
    )
    participant_line_ids = fields.One2many(
        'tna.proposed.participant',
        'proposed_training_id',
        string='Peserta Diusulkan & Biaya',
        copy=True
    )
    estimated_participant_count = fields.Integer(
        string='Jumlah Peserta Diusulkan',
        compute='_compute_totals_from_participants',
        store=True,
        tracking=True,
        help="Jumlah total peserta dari daftar di bawah."
    )
    proposed_period_char = fields.Char(
        string='Periode Pelaksanaan (Usulan)',
        help="Contoh: Semester I 2025, Kuartal 3 2025, atau Bulan Tertentu (misal: Juni 2025)",
        tracking=True
    )
    estimated_duration_days = fields.Integer(
        string='Estimasi Durasi (Hari)',
        tracking=True
    )
    estimated_duration_hours = fields.Integer(
        string='Estimasi Durasi (Jam)',
        tracking=True
    )
    estimated_cost = fields.Monetary(
        string='Total Estimasi Biaya Training',
        currency_field='currency_id',
        compute='_compute_totals_from_participants',
        store=True,
        tracking=True,
        help="Total estimasi biaya dari semua peserta yang diusulkan."
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        compute='_compute_currency_id',
        store=True,
        readonly=True
    )
    proposed_organizer = fields.Char(
        string='Usulan Penyelenggara Training',
        tracking=True
    )
    department_id = fields.Many2one(
        'hr.department',
        related='submission_id.department_id',
        string='Divisi Pengusul',
        store=True,
        index=True
    )
    branch_id = fields.Many2one(
        'res.branch',
        related='submission_id.branch_id',
        string='Cabang Pengusul',
        store=True,
        index=True
    )
    period_id = fields.Many2one(
        'tna.period',
        related='submission_id.period_id',
        string='Periode TNA',
        store=True,
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        related='submission_id.company_id',
        string='Perusahaan',
        store=True,
        readonly=True
    )
    state = fields.Selection([
        ('new', 'Baru Diinput'),
        ('pending_approval', 'Menunggu Approval SDM'),
        ('approved', 'Disetujui SDM'),
        ('rejected', 'Ditolak SDM'),
        ('realized', 'Sudah Dibuatkan Realisasi')
        ],
        string='Status Usulan Item',
        default='new',
        copy=False,
        tracking=True,
        index=True,
        group_expand='_read_group_state_ids'
    )
    rejection_reason = fields.Text(
        string='Alasan Penolakan (oleh SDM)',
        tracking=True
    )
    sdm_approver_id = fields.Many2one(
        'res.users',
        string='SDM Reviewer/Approver',
        copy=False,
        tracking=True,
        readonly=True
    )
    approval_date = fields.Datetime(
        string='Tanggal Approval/Rejection',
        copy=False,
        tracking=True,
        readonly=True
    )
    training_realization_id = fields.Many2one(
        'training.course',
        string='Link ke Realisasi Training',
        readonly=True,
        copy=False,
        ondelete='set null',
        help="Training yang direalisasikan berdasarkan usulan ini."
    )
    can_approve_or_reject = fields.Boolean(
        compute='_compute_can_approve_or_reject',
        string="Bisa Approve/Reject?"
    )
    cost_for_rekap_organik = fields.Monetary(
        string='Biaya Rekap (Organik)',
        currency_field='currency_id',
        compute='_compute_rekap_fields',
        store=True,
        help="Estimasi biaya training untuk peserta Organik"
    )
    cost_for_rekap_tad_pkwt = fields.Monetary(
        string='Biaya Rekap (TAD/PKWT)',
        currency_field='currency_id',
        compute='_compute_rekap_fields',
        store=True,
        help="Estimasi biaya training untuk peserta TAD/PKWT"
    )
    days_for_rekap_organik = fields.Integer(
        string='Hari Rekap (Organik)',
        compute='_compute_rekap_fields',
        store=True,
        help="Estimasi total hari training untuk peserta Organik (jumlah peserta x durasi)"
    )
    days_for_rekap_tad_pkwt = fields.Integer(
        string='Hari Rekap (TAD/PKWT)',
        compute='_compute_rekap_fields',
        store=True,
        help="Estimasi total hari training untuk peserta TAD/PKWT (jumlah peserta x durasi)"
    )
    participants_for_rekap_organik = fields.Integer(
        string='Peserta Rekap (Organik)',
        compute='_compute_rekap_fields',
        store=True,
        help="Jumlah peserta Organik"
    )
    participants_for_rekap_tad_pkwt = fields.Integer(
        string='Peserta Rekap (TAD/PKWT)',
        compute='_compute_rekap_fields',
        store=True,
        help="Jumlah peserta TAD/PKWT"
    )

    @api.depends('participant_line_ids.estimated_cost_participant')
    def _compute_totals_from_participants(self):
        for rec in self:
            rec.estimated_participant_count = len(rec.participant_line_ids)
            rec.estimated_cost = sum(line.estimated_cost_participant for line in rec.participant_line_ids)

    @api.depends('participant_line_ids.estimated_cost_participant', 'participant_line_ids.employment_type',
                 'estimated_duration_days')
    def _compute_rekap_fields(self):
        for rec in self:
            rec.cost_for_rekap_organik = 0
            rec.cost_for_rekap_tad_pkwt = 0
            rec.days_for_rekap_organik = 0
            rec.days_for_rekap_tad_pkwt = 0
            rec.participants_for_rekap_organik = 0
            rec.participants_for_rekap_tad_pkwt = 0

            num_organik = 0
            num_tad_pkwt = 0
            cost_organik_sum = 0.0
            cost_tad_pkwt_sum = 0.0

            for line in rec.participant_line_ids:
                if line.employment_type == 'organik':
                    num_organik += 1
                    cost_organik_sum += line.estimated_cost_participant
                elif line.employment_type in ['tad', 'pkwt']:
                    num_tad_pkwt += 1
                    cost_tad_pkwt_sum += line.estimated_cost_participant

            rec.participants_for_rekap_organik = num_organik
            rec.participants_for_rekap_tad_pkwt = num_tad_pkwt
            rec.cost_for_rekap_organik = cost_organik_sum
            rec.cost_for_rekap_tad_pkwt = cost_tad_pkwt_sum

            if rec.estimated_duration_days:
                rec.days_for_rekap_organik = num_organik * rec.estimated_duration_days
                rec.days_for_rekap_tad_pkwt = num_tad_pkwt * rec.estimated_duration_days

    @api.depends('submission_id', 'submission_id.currency_id')
    def _compute_currency_id(self):
        for rec in self:
            if rec.submission_id and rec.submission_id.currency_id:
                rec.currency_id = rec.submission_id.currency_id
            else:
                rec.currency_id = rec.company_id.currency_id or self.env.company.currency_id

    @api.onchange('submission_id')
    def _onchange_submission_id_for_related_fields_in_line(self):
        if self.submission_id:
            self.currency_id = self.submission_id.currency_id or self.company_id.currency_id or self.env.company.currency_id
            self.department_id = self.submission_id.department_id
            self.branch_id = self.submission_id.branch_id
            self.period_id = self.submission_id.period_id
            self.company_id = self.submission_id.company_id
        else:
            self.currency_id = self.env.company.currency_id
            self.department_id = False
            self.branch_id = False
            self.period_id = False
            self.company_id = self.env.company

    @api.model
    def _read_group_state_ids(self, states, domain, order):
        state_list = [key_val[0] for key_val in self._fields['state'].selection]
        return state_list

    @api.depends('state')
    def _compute_can_approve_or_reject(self):
        is_sdm_approver = self.env.user.has_group('hr.group_hr_manager')
        for rec in self:
            rec.can_approve_or_reject = is_sdm_approver and rec.state == 'pending_approval'

    def action_approve(self):
        self.ensure_one()
        if not self.can_approve_or_reject:
             raise UserError("Anda tidak memiliki hak atau usulan ini tidak dalam status yang benar untuk disetujui.")
        if self.state != 'pending_approval':
            raise UserError("Hanya usulan yang statusnya 'Menunggu Approval SDM' yang bisa disetujui.")

        self.write({
            'state': 'approved',
            'sdm_approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
            'rejection_reason': False
        })

        if self.submission_id.user_id:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=f"Usulan training '{self.name}' telah DISETUJUI",
                note=f"Usulan training '{self.name}' dari form {self.submission_id.name} telah disetujui oleh SDM. Tindak lanjut untuk realisasi dapat dilakukan.",
                user_id=self.submission_id.user_id.id
            )
        return True

    def action_reject(self):
        self.ensure_one()
        if not self.can_approve_or_reject:
             raise UserError("Anda tidak memiliki hak atau usulan ini tidak dalam status yang benar untuk ditolak.")
        if self.state != 'pending_approval':
            raise UserError("Hanya usulan yang statusnya 'Menunggu Approval SDM' yang bisa ditolak.")

        self.write({
            'state': 'rejected',
            'sdm_approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })

        if self.submission_id.user_id:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=f"Usulan training '{self.name}' DITOLAK",
                note=f"Usulan training '{self.name}' dari form {self.submission_id.name} telah ditolak. Alasan: {self.rejection_reason or 'Tidak ada alasan spesifik dari SDM.'}",
                user_id=self.submission_id.user_id.id
            )
        return True

    def action_realize_training(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError("Hanya usulan yang sudah berstatus 'Disetujui SDM' yang bisa direalisasikan.")
        if self.training_realization_id:
            raise UserError(
                f"Usulan ini sudah direalisasikan sebelumnya (Realisasi: {self.training_realization_id.name}).")

        course_participant_lines_vals = []
        if not self.participant_line_ids:
            raise UserError("Tidak ada peserta yang diusulkan dalam daftar usulan TNA untuk direalisasikan.")

        for proposed_participant in self.participant_line_ids:
            course_participant_lines_vals.append((0, 0, {
                'employee_id': proposed_participant.employee_id.id,
                'estimated_cost_from_tna': proposed_participant.estimated_cost_participant,
                'actual_cost_participant': proposed_participant.estimated_cost_participant,
                'currency_id': proposed_participant.currency_id.id,
            }))

        training_course_vals = {
            'name': self.name,
            'originating_tna_id': self.id,
            'training_scope_id': self.training_scope_id.id if self.training_scope_id else False,
            'description': self.description,
            'participant_line_ids': course_participant_lines_vals,
            'budgeted_cost': self.estimated_cost,
            'currency_id': self.currency_id.id if self.currency_id else self.env.company.currency_id.id,
            'organizer': self.proposed_organizer,
            'branch_id': self.branch_id.id if self.branch_id else False,
            'department_id': self.department_id.id if self.department_id else False,
            'company_id': self.company_id.id if self.company_id else self.env.company.id,
            'state': 'draft',
        }

        new_realization_training = self.env['training.course'].create(training_course_vals)

        self.write({
            'state': 'realized',
            'training_realization_id': new_realization_training.id
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.course',
            'view_mode': 'form',
            'res_id': new_realization_training.id,
            'target': 'current',
        }

    def action_set_to_pending_approval(self):
        for rec in self:
            if rec.training_realization_id:
                raise UserError(f"Tidak bisa dikembalikan ke 'Pending Approval' karena sudah ada Realisasi Training ({rec.training_realization_id.name_get()[0][1]}) yang terhubung. Harap batalkan atau hapus Realisasi Training tersebut terlebih dahulu jika ingin mengubah status usulan ini.")

            rec.write({
                'state': 'pending_approval',
                'sdm_approver_id': False,
                'approval_date': False,
                'rejection_reason': False,
            })
            rec.activity_unlink(['mail.mail_activity_data_todo'])
        return True