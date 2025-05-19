from odoo import models, fields, api
from .training_fuzzy_decision import evaluate_training_effectiveness


class TrainingEvaluation(models.Model):
    _name = 'training.evaluation'
    _description = 'Training Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(related='employee_id.name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Nama Karyawan', required=True)
    employee_status = fields.Char(string="Status Kepegawaian", compute='_compute_employee_status')
    job_position = fields.Char(string="Jabatan", compute='_compute_job_position')
    branch_id = fields.Many2one('res.branch', string="Penempatan")
    training_date_from = fields.Date(string="Tanggal Pelaksanaan Dari")
    training_date_to = fields.Date(string="Tanggal Pelaksanaan Sampai")
    training_name = fields.Char(string="Nama Training", compute='_compute_training_name')
    training_organizer = fields.Char(string="Lembaga Training")
    supervisor_id = fields.Many2one('hr.employee', string="Nama Atasan Langsung")
    total_score = fields.Integer(string="Total Nilai", compute="_compute_total_score", store=True)
    total_score_finish = fields.Integer(compute='_compute_total_score_finish', store=True)

    @api.depends('total_score')
    def _compute_total_score_finish(self):
        for rec in self:
            rec.total_score_finish = rec.total_score

    additional_file = fields.Binary(string="File")
    additional_file_ids = fields.Many2many('ir.attachment', string="File Tambahan")
    notes = fields.Text(string="Catatan Evaluasi")
    status = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')
    ], string="Status", default='draft', tracking=True)

    evaluation_line_ids = fields.One2many('training.evaluation.line', 'evaluation_id', string="Indikator Penilaian Training")

    course_id = fields.Many2one('training.course', string="Training Course", ondelete='cascade')

    keterangan_jabatan_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Jabatan', compute='_compute_jabatan_employee')
    fungsi_penugasan_id = fields.Many2one('hr.employee.fungsi.penugasan', string='Jabatan', compute='_compute_jabatan_employee')

    is_organik_pkwt_emp = fields.Boolean(compute='_compute_is_organik_pkwt_emp')
    is_tad_emp = fields.Boolean(compute='_compute_is_tad_emp')

    # final decision for training evaluation
    training_result = fields.Char(string='Hasil Training', compute='_compute_training_result', store=True)

    @api.depends('employee_id')
    def _compute_is_organik_pkwt_emp(self):
        self.is_organik_pkwt_emp = self.employee_id.employment_type in ['organik', 'pkwt']

    @api.depends('employee_id')
    def _compute_is_tad_emp(self):
        self.is_tad_emp = self.employee_id.employment_type == 'tad'

    @api.depends('employee_id')
    def _compute_jabatan_employee(self):
        self.keterangan_jabatan_id = False
        self.fungsi_penugasan_id = False
        if self.employee_id.employment_type in ['organik', 'pkwt']:
            self.keterangan_jabatan_id = self.employee_id.keterangan_jabatan_id.id
        elif self.employee_id.employment_type == 'tad':
            self.fungsi_penugasan_id = self.employee_id.fungsi_penugasan_id.id

    @api.depends('course_id')
    def _compute_training_name(self):
        for rec in self:
            for course in rec.course_id:
                rec.training_name = course.name
            else:
                rec.training_name = ''

    @api.depends('evaluation_line_ids.score')
    def _compute_total_score(self):
        for record in self:
            record.total_score = sum(int(line.score) for line in record.evaluation_line_ids)

    @api.depends('employee_id')
    def _compute_employee_status(self):
        for rec in self:
            rec.employee_status = rec.employee_id.contract_id.contract_type_id.name if (rec.employee_id.contract_id
                                                                                        and rec.employee_id.contract_id.contract_type_id) else ''

    @api.depends('employee_id')
    def _compute_job_position(self):
        for rec in self:
            rec.job_position = rec.employee_id.job_id.name if rec.employee_id.job_id else ''

    @api.model
    def default_get(self, fields_list):
        res = super(TrainingEvaluation, self).default_get(fields_list)
        if 'evaluation_line_ids' in fields_list:
            default_indicators = [
                {'indicator': 'Penerapan ilmu yang didapat dari trainning telah dilakukan dan berdampak pada kenaikan kinerja karyawan', 'score': False, 'evaluation_id': self.id},
                {'indicator': 'Pengaruh training terhadap sikap kerja dan perilaku sehari hari karyawan', 'score': False, 'evaluation_id': self.id},
                {'indicator': 'Inisiatif karyawan dalam membagikan ilmu training yang didapat kepada rekan kerja', 'score': False, 'evaluation_id': self.id},
                {'indicator': 'Manfaat dari training yang telah dilakukan karyawan terhadap kemajuan perusahaan', 'score': False, 'evaluation_id': self.id},
            ]
            res['evaluation_line_ids'] = [(0, 0, line) for line in default_indicators]
        return res

    def action_submit_evaluation(self):
        for rec in self:
            rec.status = 'posted'

    def action_set_to_draft_evaluation(self):
        for rec in self:
            rec.status = 'draft'

    @api.depends('evaluation_line_ids.score')
    def _compute_training_result(self):
        for record in self:
            scores = [int(line.score) for line in record.evaluation_line_ids if line.score]
            if scores:
                avg_score = sum(scores) / len(scores)
                fuzzy_score = evaluate_training_effectiveness(avg_score)

                if fuzzy_score >= 70:
                    record.training_result = 'Berhasil'
                elif fuzzy_score >= 50:
                    record.training_result = 'Perlu Evaluasi Ulang'
                else:
                    record.training_result = 'Gagal'
            else:
                record.training_result = 'Belum Dinilai'


class TrainingEvaluationLine(models.Model):
    _name = 'training.evaluation.line'
    _description = 'Training Evaluation Line'

    evaluation_id = fields.Many2one('training.evaluation', string="Evaluation Reference", required=True, ondelete='cascade')
    indicator = fields.Char(string="Indikator")
    score = fields.Selection([
        ('5', 'Sangat Baik (5)'),
        ('4', 'Baik (4)'),
        ('3', 'Cukup (3)'),
        ('2', 'Buruk (2)'),
        ('1', 'Sangat Buruk (1)')
    ], string="Nilai")