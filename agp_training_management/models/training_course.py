from odoo import models, fields, api
from odoo.exceptions import UserError


class TrainingCourse(models.Model):
    _name = 'training.course'
    _description = 'Pelaksanaan/Realisasi Training'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string="Nama Training/Diklat Final",
        required=True,
        tracking=True,
        index="trigram"
    )
    originating_tna_id = fields.Many2one(
        'tna.proposed.training',
        string='Asal Usulan TNA',
        readonly=True,
        copy=False,
        ondelete='restrict',
        help="Usulan TNA yang menjadi dasar pelaksanaan training ini."
    )
    state = fields.Selection([
        ('draft', 'Draft Pelaksanaan'),
        ('registered', 'Didaftarkan'),
        ('paid', 'Sudah Dibayar'),
        ('ongoing', 'Sedang Berlangsung'),
        ('completed', 'Training Selesai'),
        ('cancelled', 'Dibatalkan')
        ],
        string='Status Pelaksanaan',
        default='draft',
        copy=False,
        tracking=True,
        index=True,
        group_expand='_read_group_state_ids'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    training_scope_id = fields.Many2one('tna.training.scope', string='Lingkup Diklat')
    description = fields.Text(string='Deskripsi Training Final')
    participant_line_ids = fields.One2many(
        'training.course.participant.line',
        'course_id',
        string='Peserta Final & Biaya Realisasi',
        copy=True
    )
    budgeted_cost = fields.Monetary(string="Biaya Estimasi/Budget (dari TNA)", currency_field='currency_id')
    organizer = fields.Char(string="Penyelenggara Usulan/Final")
    branch_id = fields.Many2one('res.branch', string="Cabang")
    department_id = fields.Many2one('hr.department', string="Divisi Pengusul Awal")
    company_id = fields.Many2one(
        'res.company',
        string="Perusahaan",
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )
    actual_start_date = fields.Date(string="Tanggal Mulai Aktual", tracking=True)
    actual_end_date = fields.Date(string="Tanggal Selesai Aktual", tracking=True)
    actual_duration_days = fields.Integer(string="Durasi Aktual (Hari)", compute='_compute_actual_duration_days', store=True)
    actual_duration_hours = fields.Integer(string="Durasi Aktual (Jam)", tracking=True)

    training_location_type = fields.Selection([
        ('offline', 'Offline'),
        ('online', 'Online'),
        ('blended', 'Blended/Hybrid')
        ], string="Tipe Lokasi Training", tracking=True)
    training_location_detail = fields.Char(string="Detail Lokasi/Platform Training", tracking=True)

    actual_cost = fields.Monetary(
        string="Total Biaya Realisasi",
        currency_field='currency_id',
        compute='_compute_actual_cost_from_lines',
        store=True,
        tracking=True,
        help="Total biaya realisasi dari semua peserta."
    )

    final_organizer_vendor_id = fields.Many2one('res.partner', string="Vendor/Penyelenggara Final", domain="[('is_company','=',True)]")
    rkap_link_notes = fields.Text(string="Catatan Keterkaitan dengan RKAP")

    certificate_received = fields.Boolean(string="Sertifikat Diterima?", tracking=True)
    certificate_number = fields.Char(string="Nomor Sertifikat", tracking=True)
    certificate_issue_date = fields.Date(string="Tanggal Terbit Sertifikat", tracking=True)
    certificate_expiry_date = fields.Date(string="Tanggal Kadaluarsa Sertifikat", tracking=True)

    evaluation_ids = fields.One2many('training.evaluation', 'course_id', string="Evaluasi Training")
    evaluation_count = fields.Integer(string="Jumlah Evaluasi", compute='_compute_evaluation_count')

    @api.model
    def _read_group_state_ids(self, states, domain, order):
        state_list = [key_val[0] for key_val in self._fields['state'].selection]
        return state_list

    @api.depends('participant_line_ids.actual_cost_participant')
    def _compute_actual_cost_from_lines(self):
        for course in self:
            course.actual_cost = sum(line.actual_cost_participant for line in course.participant_line_ids)

    @api.depends('actual_start_date', 'actual_end_date')
    def _compute_actual_duration_days(self):
        for rec in self:
            if rec.actual_start_date and rec.actual_end_date:
                delta = rec.actual_end_date - rec.actual_start_date
                rec.actual_duration_days = delta.days + 1
            else:
                rec.actual_duration_days = 0

    @api.depends('participant_line_ids')
    def _compute_evaluation_count(self):
        for record in self:
            try:
                record.evaluation_count = self.env['training.evaluation'].search_count([('course_id', '=', record.id)])
            except KeyError:
                record.evaluation_count = 0

    def action_set_state_completed(self):
        self.ensure_one()
        res = self.write({'state': 'completed'})

        if res and self.state == 'completed':
            CompletedTraining = self.env['hr.employee.completed.training']
            TrainingEvaluation = self.env['training.evaluation']

            for line in self.participant_line_ids:
                employee = line.employee_id
                if not employee:
                    continue

                existing_completed_training = CompletedTraining.search([
                    ('employee_id', '=', employee.id),
                    ('realization_id', '=', self.id)
                ], limit=1)
                if not existing_completed_training:
                    CompletedTraining.create({
                        'employee_id': employee.id,
                        'realization_id': self.id,
                    })

                existing_evaluation = TrainingEvaluation.search([
                    ('employee_id', '=', employee.id),
                    ('course_id', '=', self.id)
                ], limit=1)
                if not existing_evaluation:
                    eval_vals = TrainingEvaluation.default_get(TrainingEvaluation.fields_get_keys())
                    eval_vals.update({
                        'employee_id': employee.id,
                        'course_id': self.id,
                        'branch_id': self.branch_id.id if self.branch_id else False,
                        'training_date_from': self.actual_start_date,
                        'training_date_to': self.actual_end_date,
                        'training_organizer': self.organizer,
                        'supervisor_id': employee.parent_id.id if employee.parent_id else False,
                    })
                    TrainingEvaluation.create(eval_vals)
        return res

    def action_register(self):
        self.write({'state': 'registered'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_start_training(self):
        if not self.actual_start_date:
            raise UserError("Harap isi Tanggal Mulai Aktual sebelum memulai training.")
        self.write({'state': 'ongoing'})

    def action_complete_training(self):
        if not self.actual_end_date:
            raise UserError("Harap isi Tanggal Selesai Aktual sebelum menyelesaikan training.")
        if self.actual_start_date and self.actual_end_date and self.actual_end_date < self.actual_start_date:
            raise UserError("Tanggal Selesai Aktual tidak boleh sebelum Tanggal Mulai Aktual.")
        return self.action_set_state_completed()

    def action_cancel_training(self):
        self.write({'state': 'cancelled'})
        if self.originating_tna_id and self.originating_tna_id.state == 'realized':
            self.originating_tna_id.write({'state': 'approved', 'training_realization_id': False})

    def action_reset_to_draft_realization(self):
        if self.state not in ['cancelled', 'registered']:
            raise UserError(
                "Hanya training yang statusnya Dibatalkan atau Didaftarkan (dan belum ada proses lanjut) yang bisa direset ke draft.")
        self.env['hr.employee.completed.training'].search([('realization_id', '=', self.id)]).unlink()
        self.evaluation_ids.unlink()
        self.write({'state': 'draft'})